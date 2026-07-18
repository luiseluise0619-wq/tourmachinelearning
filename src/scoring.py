"""FestCast 핵심 엔진 — 흥행도 점수 · 보완 피드백 · 마케팅 추천.

이 모듈이 FestCast의 '두뇌'다. 축제 기획안 + 주변 인구 + 날씨 전망을 받아
    ① 흥행도 점수(0~100)와 예상 방문자수
    ② 약점 진단 + "이렇게 바꾸면 +N%" 보완 피드백(what-if)
    ③ 주변 인구 기반 타깃·홍보 채널·프로그램 추천
을 하나의 리포트로 만든다.

지금은 **규칙 기반 가중합**이다. 실데이터가 쌓이면 각 factor 의 가중치와
방문자 추정식을 학습 모델(XGBoost/LightGBM)로 교체하는 구조로 설계했다.
(docs/architecture.md 참고)

바로 실행:
    python -m src.scoring        # 샘플 기획안으로 데모 리포트 출력
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ────────────────────────────────────────────────────────────
# 입력 데이터 구조
# ────────────────────────────────────────────────────────────
@dataclass
class FestivalPlan:
    """축제 기획안."""
    name: str
    region: str                 # 개최 지역명
    month: int                  # 개최 월 (1~12)
    is_outdoor: bool            # 실외 여부 (날씨 민감도)
    is_weekend: bool            # 주말/공휴일 개최 여부
    num_programs: int           # 프로그램 개수(다양성)
    has_experience: bool = False   # 체험형 프로그램 포함
    has_food: bool = False         # 먹거리 존재
    has_performance: bool = False  # 공연/무대 존재
    budget_manwon: int = 0         # 예산(만원)
    # 외국인 유치 관련 (한국관광공사 핵심 관심사)
    has_kcontent: bool = False     # K콘텐츠 연계 여부(드라마 촬영지·K팝·한류스타 등)
    kcontent_desc: str = ""        # 연계 콘텐츠 설명
    near_intl_gateway: bool = False  # 공항·KTX 등 외국인 접근성 양호 지역


@dataclass
class RegionDemographics:
    """주변 지역 인구 통계 (반경 내 합산). 연령대별 인구 수."""
    total_population: int
    # 연령대 키: '10s','20s','30s','40s','50s','60s+'
    age_counts: dict[str, int] = field(default_factory=dict)
    female_ratio: float = 0.5   # 여성 비율(0~1)

    def dominant_age(self) -> str:
        if not self.age_counts:
            return "unknown"
        return max(self.age_counts, key=self.age_counts.get)

    def age_share(self, key: str) -> float:
        tot = sum(self.age_counts.values()) or 1
        return self.age_counts.get(key, 0) / tot


@dataclass
class WeatherOutlook:
    """개최 시기 날씨 전망."""
    avg_temp_c: float           # 평균 기온(℃)
    rain_prob: float            # 강수 확률(0~1)


# ────────────────────────────────────────────────────────────
# 개별 요인 점수 (각 0~100)
# ────────────────────────────────────────────────────────────
def weather_fit_score(plan: FestivalPlan, wx: WeatherOutlook) -> float:
    """날씨 적합도. 실외 축제일수록 강수/기온 페널티가 커진다."""
    # 기온 쾌적도: 15~25℃ 를 최적으로, 멀어질수록 감점
    temp_penalty = min(abs(wx.avg_temp_c - 20) * 2.5, 60)
    # 강수 페널티: 실외면 최대 -60, 실내면 완화
    rain_weight = 60 if plan.is_outdoor else 20
    rain_penalty = wx.rain_prob * rain_weight
    return _clip(100 - temp_penalty - rain_penalty)


def demand_score(plan: FestivalPlan, demo: RegionDemographics) -> float:
    """수요 기반. 주변 인구 규모가 클수록 잠재 방문자 풀이 크다."""
    # 인구 규모를 로그 스케일로 0~100 매핑 (5만=낮음, 100만=높음)
    import math
    pop = max(demo.total_population, 1)
    scaled = (math.log10(pop) - 4.0) / (6.0 - 4.0)   # 1만~100만 → 0~1
    return _clip(scaled * 100)


def program_score(plan: FestivalPlan) -> float:
    """프로그램 매력도. 다양성 + 핵심 구성요소(체험·먹거리·공연)."""
    diversity = min(plan.num_programs, 10) / 10 * 50   # 최대 50
    richness = (
        (15 if plan.has_experience else 0)
        + (15 if plan.has_food else 0)
        + (20 if plan.has_performance else 0)
    )
    return _clip(diversity + richness)


def timing_score(plan: FestivalPlan) -> float:
    """개최 시기. 주말/성수기(봄·가을) 가점."""
    weekend = 40 if plan.is_weekend else 15
    peak = 40 if plan.month in (4, 5, 9, 10) else (
        20 if plan.month in (3, 6, 8, 11) else 10)   # 혹한·혹서·장마 감점
    return _clip(weekend + peak + 20)


# 흥행도 가중치 (실데이터 회귀로 학습 시 교체될 지점)
WEIGHTS = {"weather": 0.30, "demand": 0.30, "program": 0.25, "timing": 0.15}


def appeal_score(plan: FestivalPlan, demo: RegionDemographics,
                 wx: WeatherOutlook) -> dict:
    """흥행도 종합 점수(0~100)와 요인별 분해."""
    factors = {
        "weather": weather_fit_score(plan, wx),
        "demand": demand_score(plan, demo),
        "program": program_score(plan),
        "timing": timing_score(plan),
    }
    total = sum(factors[k] * WEIGHTS[k] for k in WEIGHTS)
    return {"score": round(total, 1), "factors": {k: round(v, 1) for k, v in factors.items()}}


def estimate_visitors(plan: FestivalPlan, demo: RegionDemographics,
                      score: float) -> int:
    """예상 방문자수 추정 (규칙 기반 근사).

    주변 인구의 일정 비율이 흥행도에 비례해 방문한다고 가정.
    실데이터 확보 시 '증분 방문자' 회귀로 교체(docs/architecture.md §4).
    """
    reach_rate = 0.005 + 0.045 * (score / 100)   # 흥행도 0→0.5%, 100→5%
    base = demo.total_population * reach_rate
    if plan.is_weekend:
        base *= 1.3
    return int(base)


# 외국인 유치 계수 (실데이터/한국관광공사 방한 통계로 보정할 지점)
FOREIGN_BASE_RATIO = 0.03        # 흥행 축제 방문자 중 외국인 기본 비율(3%)
KCONTENT_MULTIPLIER = 4.0        # K콘텐츠 연계 시 외국인 유입 배수
GATEWAY_MULTIPLIER = 1.5         # 공항·KTX 인접 등 접근성 보정


def estimate_visitor_split(plan: FestivalPlan, demo: RegionDemographics,
                           score: float) -> dict:
    """총 방문자를 내국인/외국인으로 분리하고 K콘텐츠 효과를 정량화한다.

    핵심: 같은 축제라도 K콘텐츠(드라마 촬영지·K팝·한류) 연계 시
    외국인 방문이 크게 늘어난다는 걸 "연계 시 vs 미연계 시"로 비교해 보여준다.
    한국관광공사(주최)의 최대 관심사인 방한 외국인 유치를 정조준한 지표.
    """
    total = estimate_visitors(plan, demo, score)

    # 접근성에 따른 외국인 기본 유입
    gateway = GATEWAY_MULTIPLIER if plan.near_intl_gateway else 1.0

    # 미연계(baseline) 외국인
    foreign_wo = total * FOREIGN_BASE_RATIO * gateway
    # 연계 시 외국인 (K콘텐츠는 흥행 점수가 높을수록 파급도 커짐)
    kcontent_boost = KCONTENT_MULTIPLIER * (0.6 + 0.4 * score / 100)
    foreign_with = foreign_wo * kcontent_boost

    # 실제 채택되는 외국인 추정치는 기획안의 K콘텐츠 연계 여부에 따름
    foreign = foreign_with if plan.has_kcontent else foreign_wo
    domestic = max(total - foreign, 0)

    return {
        "total": total,
        "domestic": int(domestic),
        "foreign": int(foreign),
        "foreign_ratio": round(foreign / total * 100, 1) if total else 0.0,
        # K콘텐츠 연계 효과 (핵심 인사이트)
        "kcontent_effect": {
            "foreign_without_kcontent": int(foreign_wo),
            "foreign_with_kcontent": int(foreign_with),
            "delta": int(foreign_with - foreign_wo),
            "uplift_pct": round((foreign_with / foreign_wo - 1) * 100, 0)
            if foreign_wo else 0.0,
        },
    }


# ────────────────────────────────────────────────────────────
# ② 보완 피드백 (what-if 처방)
# ────────────────────────────────────────────────────────────
def generate_feedback(plan: FestivalPlan, demo: RegionDemographics,
                      wx: WeatherOutlook) -> list[dict]:
    """약한 요인마다 구체적 처방과 예상 효과를 생성한다."""
    fb: list[dict] = []
    result = appeal_score(plan, demo, wx)
    f = result["factors"]

    # 날씨 약점
    if f["weather"] < 60:
        if plan.is_outdoor and wx.rain_prob >= 0.4:
            gain = round((weather_fit_score(_replace(plan, is_outdoor=False), wx)
                          - f["weather"]) * WEIGHTS["weather"], 1)
            fb.append(_fb("날씨 리스크",
                          f"강수확률 {int(wx.rain_prob*100)}% — 실외 진행 시 흥행 급락 위험",
                          "우천 대비 실내 대체공간 또는 캐노피/천막 확보, 우천 프로그램 마련",
                          gain))
        if abs(wx.avg_temp_c - 20) > 8:
            fb.append(_fb("기온 부적합",
                          f"개최 시기 평균 {wx.avg_temp_c}℃ — 관람 쾌적도 저하",
                          "그늘막·난방/냉방 쉼터 배치, 개최 시간대 조정(더위·추위 회피)",
                          None))

    # 시기 약점
    if not plan.is_weekend:
        gain = round((timing_score(_replace(plan, is_weekend=True))
                      - f["timing"]) * WEIGHTS["timing"], 1)
        fb.append(_fb("평일 개최",
                      "평일 개최는 방문 접근성이 낮음",
                      "주말·공휴일 포함 일정으로 조정",
                      gain))
    if plan.month in (1, 2, 7, 12):
        fb.append(_fb("비수기/기상 리스크 시기",
                      "혹한·혹서·장마 시기 개최는 방문 저하 위험",
                      "봄(4~5월)·가을(9~10월) 성수기로 일정 이동 검토",
                      None))

    # 프로그램 약점
    if f["program"] < 60:
        missing = []
        if not plan.has_experience:
            missing.append("체험형 프로그램")
        if not plan.has_food:
            missing.append("먹거리 존재")
        if not plan.has_performance:
            missing.append("공연/무대")
        if missing:
            fb.append(_fb("프로그램 빈약",
                          f"부족 요소: {', '.join(missing)}",
                          f"{missing[0]} 우선 보강 — 체류시간·재방문 유도",
                          None))

    # 수요 약점
    if f["demand"] < 50:
        fb.append(_fb("주변 수요 부족",
                      f"주변 인구 {demo.total_population:,}명으로 잠재 방문 풀이 작음",
                      "인근 도시 대상 광역 홍보 + 관광버스/셔틀 연계로 도달 범위 확대",
                      None))

    # 외국인 유치 기회 (K콘텐츠 미연계 시)
    if not plan.has_kcontent:
        split = estimate_visitor_split(plan, demo, result["score"])
        eff = split["kcontent_effect"]
        fb.append(_fb("외국인 유치 기회 미활용",
                      f"현재 예상 외국인 {split['foreign']:,}명 — K콘텐츠 미연계",
                      "인근 드라마 촬영지·K팝/한류 콘텐츠와 연계 프로그램 구성 "
                      "(포토존·투어·굿즈) + 외국어 안내·다국어 SNS 홍보",
                      None,
                      extra={"expected_foreign_uplift":
                             f"외국인 약 {eff['delta']:,}명 추가 (+{eff['uplift_pct']:.0f}%) 기대"}))

    return fb


# ────────────────────────────────────────────────────────────
# ③ 마케팅 / 타깃 추천 (주변 인구 기반)
# ────────────────────────────────────────────────────────────
# 연령대 → 채널·메시지·프로그램 매핑
_SEGMENT_PLAYBOOK = {
    "10s": {"channels": ["인스타그램/틱톡 릴스", "학교 연계 홍보"],
            "tone": "트렌디·포토스팟 강조", "program": "포토존·SNS 이벤트·버스킹"},
    "20s": {"channels": ["인스타그램", "네이버 지역 카페", "대학 커뮤니티"],
            "tone": "감성·체험 중심", "program": "체험부스·야간 공연·플리마켓"},
    "30s": {"channels": ["인스타그램", "맘카페", "당근마켓 지역광고"],
            "tone": "가족·아이 동반 안심", "program": "키즈존·체험형·먹거리"},
    "40s": {"channels": ["맘카페", "지역 현수막", "카카오 지역채널"],
            "tone": "가족 나들이·먹거리", "program": "먹거리장터·가족 체험"},
    "50s": {"channels": ["지역 신문/방송", "현수막", "관광버스 연계"],
            "tone": "향수·문화·건강", "program": "공연·전통문화·먹거리"},
    "60s+": {"channels": ["지역 방송/라디오", "경로당·복지관 연계", "현수막"],
             "tone": "건강·전통·편의", "program": "전통공연·휴게공간·셔틀"},
}


def recommend_marketing(demo: RegionDemographics) -> dict:
    """주변 인구 통계에서 타깃 세그먼트와 홍보 전략을 도출한다."""
    dom = demo.dominant_age()
    play = _SEGMENT_PLAYBOOK.get(dom, {})
    gender_note = (
        "여성 비중 높음 — 체험·감성 콘텐츠 강화"
        if demo.female_ratio >= 0.53 else
        "남성 비중 높음 — 스포츠·먹거리·야외활동 강화"
        if demo.female_ratio <= 0.47 else
        "성비 균형 — 폭넓은 프로그램 구성"
    )
    # 상위 2개 세그먼트
    top2 = sorted(demo.age_counts.items(), key=lambda kv: kv[1], reverse=True)[:2]
    return {
        "primary_segment": dom,
        "segment_shares": {k: round(demo.age_share(k) * 100, 1) for k, _ in top2},
        "recommended_channels": play.get("channels", []),
        "message_tone": play.get("tone", ""),
        "program_focus": play.get("program", ""),
        "gender_insight": gender_note,
    }


# ────────────────────────────────────────────────────────────
# 종합 리포트
# ────────────────────────────────────────────────────────────
def build_report(plan: FestivalPlan, demo: RegionDemographics,
                 wx: WeatherOutlook) -> dict:
    """흥행 예보 리포트 전체를 조립한다."""
    appeal = appeal_score(plan, demo, wx)
    return {
        "festival": plan.name,
        "region": plan.region,
        "appeal_score": appeal["score"],
        "grade": _grade(appeal["score"]),
        "factor_breakdown": appeal["factors"],
        "visitors": estimate_visitor_split(plan, demo, appeal["score"]),
        "feedback": generate_feedback(plan, demo, wx),
        "marketing": recommend_marketing(demo),
    }


# ────────────────────────────────────────────────────────────
# 헬퍼
# ────────────────────────────────────────────────────────────
def _clip(x: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, x))


def _grade(score: float) -> str:
    if score >= 80:
        return "A (흥행 유력)"
    if score >= 65:
        return "B (양호)"
    if score >= 50:
        return "C (보통·보완 필요)"
    return "D (재검토 권장)"


def _fb(issue: str, diagnosis: str, action: str, expected_gain,
        extra: dict | None = None) -> dict:
    d = {"issue": issue, "diagnosis": diagnosis, "action": action}
    if expected_gain is not None and expected_gain > 0:
        d["expected_gain"] = f"+{expected_gain}점"
    if extra:
        d.update(extra)
    return d


def _replace(plan: FestivalPlan, **changes) -> FestivalPlan:
    from dataclasses import replace
    return replace(plan, **changes)


# ────────────────────────────────────────────────────────────
# 데모
# ────────────────────────────────────────────────────────────
def _demo() -> None:
    import json
    plan = FestivalPlan(
        name="○○ 벚꽃 야행 축제", region="경기 ○○시",
        month=7, is_outdoor=True, is_weekend=False,
        num_programs=4, has_experience=False, has_food=True,
        has_performance=True, budget_manwon=30000,
    )
    demo = RegionDemographics(
        total_population=120_000,
        age_counts={"10s": 9000, "20s": 14000, "30s": 22000,
                    "40s": 26000, "50s": 21000, "60s+": 28000},
        female_ratio=0.54,
    )
    wx = WeatherOutlook(avg_temp_c=29.0, rain_prob=0.6)

    report = build_report(plan, demo, wx)
    print("=== 흥행 예보 리포트 ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # K콘텐츠 연계 시 vs 미연계 시 외국인 방문 비교
    print("\n=== K콘텐츠 연계 효과 (외국인 방문) ===")
    score = report["appeal_score"]
    without = estimate_visitor_split(_replace(plan, has_kcontent=False), demo, score)
    withk = estimate_visitor_split(_replace(plan, has_kcontent=True), demo, score)
    print(f"미연계 외국인: {without['foreign']:,}명")
    print(f"K콘텐츠 연계 외국인: {withk['foreign']:,}명 "
          f"(+{withk['foreign'] - without['foreign']:,}명, "
          f"+{withk['kcontent_effect']['uplift_pct']:.0f}%)")


if __name__ == "__main__":
    _demo()
