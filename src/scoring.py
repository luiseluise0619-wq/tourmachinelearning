"""FestCast 핵심 엔진 — 흥행도 점수 · 확률 예보 · 보완 피드백 · 마케팅 추천.

이 모듈이 FestCast의 '두뇌'다. 축제 기획안 + 주변 인구 + 지역 여건 + 날씨 +
거시환경을 받아
    ① 흥행도 점수(0~100)와 예상 방문자수 (내국인/외국인 분리)
    ② 100명 단위 확률 예보 + 쏠림(수용초과) 위험
    ③ 약점 진단 + "이렇게 바꾸면 +N" 보완 피드백(what-if)
    ④ 주변 인구 기반 타깃·홍보 채널·프로그램 추천
을 하나의 리포트로 만든다.

흥행도는 5개 요인의 가중합이다:
    weather(날씨) · demand(수요·접근성) · program(프로그램) ·
    timing(시기) · reputation(평판·이력·홍보)

지금은 **규칙 기반**이다. 실데이터가 쌓이면 각 factor 가중치와 방문자 추정식을
학습 모델(XGBoost/LightGBM 회귀 + 분위수 회귀)로 교체하는 구조로 설계했다.
(docs/architecture.md, docs/features.md 참고)

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
    """축제 기획안 (기획자가 정하거나 아는 값)."""
    name: str
    region: str                 # 개최 지역명
    month: int                  # 개최 월 (1~12)
    is_outdoor: bool            # 실외 여부 (날씨 민감도)
    is_weekend: bool            # 주말/공휴일 개최 여부
    num_programs: int           # 프로그램 개수(다양성)
    # 프로그램 구성
    has_experience: bool = False   # 체험형 프로그램 포함
    has_food: bool = False         # 먹거리 존재
    has_performance: bool = False  # 공연/무대 존재
    has_celebrity: bool = False    # 유명 아티스트/셀럽 출연
    duration_days: int = 1         # 축제 기간(일수)
    is_free: bool = True           # 입장 무료 여부
    budget_manwon: int = 0         # 예산(만원)
    # 외국인 유치 (한국관광공사 핵심 관심사)
    has_kcontent: bool = False     # K콘텐츠 연계(드라마 촬영지·K팝·한류)
    kcontent_desc: str = ""        # 연계 콘텐츠 설명
    near_intl_gateway: bool = False  # 공항·KTX 등 외국인 접근성 양호
    # 시기 심화
    near_holiday: bool = False     # 연휴/황금연휴 인접
    during_vacation: bool = False  # 방학 기간
    nature_peak_match: float = 1.0  # 자연물(벚꽃·단풍) 절정 일치도 0~1 (비자연축제=1.0)
    # 평판·이력 (시점정합: 직전 회차까지만)
    festival_grade: str = "none"   # 지정등급 global/culture/expected/none
    prev_visitors: int | None = None  # 직전 회차 방문자수
    num_editions: int = 1          # 몇 회째 축제인가
    # 홍보 투입
    promo_budget_manwon: int = 0   # 홍보 예산(만원)
    promo_channels: int = 0        # 홍보 채널 수
    preorders: int = 0             # 사전 예매·예약 건수(선행지표)


@dataclass
class RegionContext:
    """개최 지역 여건 (접근성·경쟁·관광 인프라)."""
    distance_to_seoul_km: float = 100.0   # 수도권에서의 거리
    distance_to_station_km: float = 10.0  # KTX역/터미널까지 거리
    has_shuttle: bool = False             # 셔틀버스 운영
    parking_capacity: int = 0             # 주차 규모(대)
    nearby_festivals_same_week: int = 0   # 같은 주말 인근 축제 수(경쟁)
    lodging_count: int = 0                # 인근 숙박 시설 수
    restaurant_count: int = 0             # 인근 음식점 수


@dataclass
class MacroContext:
    """거시·외부 환경 (시점정합: 그 시점까지 값만)."""
    exchange_rate_krw_usd: float = 1300.0  # 원/달러 (원화 약세=외국인 유리)
    pandemic_index: float = 0.0            # 0(정상)~1(심각): 방문 억제


@dataclass
class RegionDemographics:
    """주변 지역 인구 통계 (반경 내 합산). 연령대별 인구 수."""
    total_population: int
    age_counts: dict[str, int] = field(default_factory=dict)  # '10s'~'60s+'
    female_ratio: float = 0.5

    def dominant_age(self) -> str:
        if not self.age_counts:
            return "unknown"
        return max(self.age_counts, key=self.age_counts.get)

    def age_share(self, key: str) -> float:
        tot = sum(self.age_counts.values()) or 1
        return self.age_counts.get(key, 0) / tot


@dataclass
class WeatherOutlook:
    """개최 시기 날씨 전망 (평년값 기반)."""
    avg_temp_c: float           # 평균 기온(℃)
    rain_prob: float            # 강수 확률(0~1)


# ────────────────────────────────────────────────────────────
# 개별 요인 점수 (각 0~100)
# ────────────────────────────────────────────────────────────
def weather_fit_score(plan: FestivalPlan, wx: WeatherOutlook) -> float:
    """날씨 적합도. 실외 축제일수록 강수/기온 페널티가 커진다."""
    temp_penalty = min(abs(wx.avg_temp_c - 20) * 2.5, 60)
    rain_weight = 60 if plan.is_outdoor else 20
    rain_penalty = wx.rain_prob * rain_weight
    return _clip(100 - temp_penalty - rain_penalty)


def demand_score(plan: FestivalPlan, demo: RegionDemographics,
                 region: RegionContext) -> float:
    """수요 기반. 주변 인구 + 접근성 + 관광 인프라 − 경쟁."""
    import math
    pop = max(demo.total_population, 1)
    pop_score = _clip((math.log10(pop) - 4.0) / 2.0 * 100) * 0.50   # 최대 50

    access = (
        _clip(12 * (1 - region.distance_to_seoul_km / 200), 0, 12)     # 수도권 근접
        + _clip(8 * (1 - region.distance_to_station_km / 30), 0, 8)    # 역 근접
        + (5 if region.has_shuttle else 0)                            # 셔틀
        + min(region.parking_capacity / 500, 1) * 5                    # 주차
    )                                                                 # 최대 30
    infra = min(region.lodging_count / 100 + region.restaurant_count / 500,
                1) * 20                                               # 최대 20
    competition = min(region.nearby_festivals_same_week * 6, 25)       # 경쟁 감점
    return _clip(pop_score + access + infra - competition)


def program_score(plan: FestivalPlan) -> float:
    """프로그램 매력도. 다양성 + 구성 + 셀럽 + 무료 + 기간."""
    diversity = min(plan.num_programs, 10) / 10 * 30
    richness = ((10 if plan.has_experience else 0)
                + (8 if plan.has_food else 0)
                + (12 if plan.has_performance else 0))
    celebrity = 15 if plan.has_celebrity else 0
    free = 10 if plan.is_free else 0
    duration = min(plan.duration_days, 4) / 4 * 15
    return _clip(diversity + richness + celebrity + free + duration)


def timing_score(plan: FestivalPlan) -> float:
    """개최 시기. 주말 + 성수기 + 연휴 + 방학 + 자연물 절정 일치."""
    weekend = 25 if plan.is_weekend else 8
    peak = 30 if plan.month in (4, 5, 9, 10) else (
        18 if plan.month in (3, 6, 8, 11) else 8)
    holiday = 15 if plan.near_holiday else 0
    vacation = 10 if plan.during_vacation else 0
    nature = _clip(plan.nature_peak_match, 0, 1) * 20
    return _clip(weekend + peak + holiday + vacation + nature)


def reputation_score(plan: FestivalPlan) -> float:
    """평판·이력·홍보. 지정등급 + 개최 이력 + 과거 방문 추이 + 홍보 투입."""
    import math
    grade = {"global": 40, "culture": 30, "expected": 20}.get(plan.festival_grade, 8)
    editions = min(plan.num_editions, 10) / 10 * 20
    if plan.prev_visitors:
        prev = _clip((math.log10(max(plan.prev_visitors, 1)) - 2.0) / 3.0 * 20, 0, 20)
    else:
        prev = 8   # 신규 축제 중립값
    promo = (min(plan.promo_budget_manwon / 2000, 1) * 8
             + min(plan.promo_channels / 5, 1) * 6
             + min(plan.preorders / 1000, 1) * 6)                      # 최대 20
    return _clip(grade + editions + prev + promo)


# 흥행도 가중치 (실데이터 회귀로 학습 시 교체될 지점)
WEIGHTS = {"weather": 0.20, "demand": 0.25, "program": 0.20,
           "timing": 0.15, "reputation": 0.20}


def appeal_score(plan: FestivalPlan, demo: RegionDemographics,
                 wx: WeatherOutlook, region: RegionContext | None = None) -> dict:
    """흥행도 종합 점수(0~100)와 요인별 분해."""
    region = region or RegionContext()
    factors = {
        "weather": weather_fit_score(plan, wx),
        "demand": demand_score(plan, demo, region),
        "program": program_score(plan),
        "timing": timing_score(plan),
        "reputation": reputation_score(plan),
    }
    total = sum(factors[k] * WEIGHTS[k] for k in WEIGHTS)
    return {"score": round(total, 1),
            "factors": {k: round(v, 1) for k, v in factors.items()}}


def estimate_visitors(plan: FestivalPlan, demo: RegionDemographics,
                      score: float, macro: MacroContext | None = None) -> int:
    """예상 방문자수 추정 (규칙 기반 근사).

    두 경로로 추정한다:
      · 재개최 축제(전년 실측 보유): 전년 방문객을 기준점으로 흥행 조건에 따라 ±조정.
        (전년 방문객이 미래 방문의 가장 강한 예측변수)
      · 신규 축제: 주변 인구 × 흥행도 비례 도달률로 추정.
    감염병 상황은 두 경로 모두 방문을 억제.
    실데이터 확보 시 회귀 모델로 교체(docs/architecture.md §4).
    """
    macro = macro or MacroContext()
    if plan.prev_visitors and plan.prev_visitors > 0:
        # 흥행도 50점=전년 유지(×1.0), 100점=×1.3, 0점=×0.7
        adj = 0.7 + 0.6 * (score / 100)
        base = plan.prev_visitors * adj
    else:
        reach_rate = 0.005 + 0.045 * (score / 100)
        base = demo.total_population * reach_rate
        if plan.is_weekend:
            base *= 1.3
        base *= (1 + 0.15 * min(plan.duration_days - 1, 3))   # 기간 누적(체감)
    base *= (1 - 0.7 * _clip(macro.pandemic_index, 0, 1))     # 감염병 억제
    return int(base)


# 외국인 유치 계수 (실데이터/한국관광공사 방한 통계로 보정할 지점)
FOREIGN_BASE_RATIO = 0.03        # 흥행 축제 방문자 중 외국인 기본 비율(3%)
KCONTENT_MULTIPLIER = 4.0        # K콘텐츠 연계 시 외국인 유입 배수
GATEWAY_MULTIPLIER = 1.5         # 공항·KTX 인접 등 접근성 보정


def estimate_visitor_split(plan: FestivalPlan, demo: RegionDemographics,
                           score: float, macro: MacroContext | None = None) -> dict:
    """총 방문자를 내국인/외국인으로 분리하고 K콘텐츠 효과를 정량화한다.

    외국인은 K콘텐츠 연계·국제 접근성·환율(원화 약세)에 크게 좌우된다.
    한국관광공사(주최)의 최대 관심사인 방한 외국인 유치를 정조준한 지표.
    """
    macro = macro or MacroContext()
    total = estimate_visitors(plan, demo, score, macro)

    gateway = GATEWAY_MULTIPLIER if plan.near_intl_gateway else 1.0
    exch = _clip(macro.exchange_rate_krw_usd / 1300, 0.8, 1.4)   # 원화 약세=외국인↑

    foreign_wo = total * FOREIGN_BASE_RATIO * gateway * exch
    kcontent_boost = KCONTENT_MULTIPLIER * (0.6 + 0.4 * score / 100)
    foreign_with = foreign_wo * kcontent_boost

    foreign = foreign_with if plan.has_kcontent else foreign_wo
    domestic = max(total - foreign, 0)

    return {
        "total": total,
        "domestic": int(domestic),
        "foreign": int(foreign),
        "foreign_ratio": round(foreign / total * 100, 1) if total else 0.0,
        "kcontent_effect": {
            "foreign_without_kcontent": int(foreign_wo),
            "foreign_with_kcontent": int(foreign_with),
            "delta": int(foreign_with - foreign_wo),
            "uplift_pct": round((foreign_with / foreign_wo - 1) * 100, 0)
            if foreign_wo else 0.0,
        },
    }


# ────────────────────────────────────────────────────────────
# ①-b 확률 예보 (몬테카를로) — 100명 단위 방문자 분포 + 쏠림 위험
# ────────────────────────────────────────────────────────────
def forecast_distribution(plan: FestivalPlan, demo: RegionDemographics,
                          wx: WeatherOutlook, region: RegionContext | None = None,
                          macro: MacroContext | None = None,
                          capacity: int | None = None,
                          n_sims: int = 3000, bucket: int = 100,
                          seed: int = 42) -> dict:
    """방문자수를 점추정 대신 **확률분포**로 예보한다.

    날씨는 평년값을 중심으로 불확실하므로 날씨 시나리오를 수천 번 샘플링해
    매번 방문자수를 계산하고 100명 단위 버킷으로 확률을 집계한다.
    수용인원(capacity)을 주면 초과 확률(쏠림 위험)까지 산출 — 과제 9 정조준.

    실데이터 확보 시 LightGBM 분위수 회귀(objective='quantile')로 교체 가능.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    temps = rng.normal(wx.avg_temp_c, 3.0, n_sims)
    rained = rng.random(n_sims) < wx.rain_prob
    demand_noise = rng.lognormal(mean=0.0, sigma=0.15, size=n_sims)

    counts = np.empty(n_sims)
    for i in range(n_sims):
        sim_wx = WeatherOutlook(avg_temp_c=float(temps[i]),
                                rain_prob=1.0 if rained[i] else 0.0)
        s = appeal_score(plan, demo, sim_wx, region)["score"]
        counts[i] = estimate_visitors(plan, demo, s, macro) * demand_noise[i]

    counts = np.clip(counts, 0, None)

    lo = int(counts.min() // bucket * bucket)
    hi = int(counts.max() // bucket * bucket + bucket)
    edges = np.arange(lo, hi + bucket, bucket)
    hist, _ = np.histogram(counts, bins=edges)
    probs = hist / n_sims
    buckets = [
        {"range": f"{int(edges[j]):,}~{int(edges[j+1]):,}명",
         "prob_pct": round(float(probs[j]) * 100, 1)}
        for j in range(len(hist)) if probs[j] * 100 >= 0.1
    ]

    result = {
        "expected": int(np.mean(counts)),
        "p10": int(np.percentile(counts, 10)),
        "p50": int(np.percentile(counts, 50)),
        "p90": int(np.percentile(counts, 90)),
        "interval_80": [int(np.percentile(counts, 10)),
                        int(np.percentile(counts, 90))],
        "buckets": buckets,
    }
    if capacity is not None:
        over = float(np.mean(counts > capacity))
        result["capacity"] = capacity
        result["overcrowding_prob_pct"] = round(over * 100, 1)
        result["overcrowding_risk"] = (
            "높음" if over >= 0.3 else "주의" if over >= 0.1 else "낮음"
        )
    return result


# ────────────────────────────────────────────────────────────
# ② 보완 피드백 (what-if 처방)
# ────────────────────────────────────────────────────────────
def generate_feedback(plan: FestivalPlan, demo: RegionDemographics,
                      wx: WeatherOutlook, region: RegionContext | None = None,
                      macro: MacroContext | None = None) -> list[dict]:
    """약한 요인마다 구체적 처방과 예상 효과를 생성한다."""
    region = region or RegionContext()
    macro = macro or MacroContext()
    fb: list[dict] = []
    result = appeal_score(plan, demo, wx, region)
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
        fb.append(_fb("평일 개최", "평일 개최는 방문 접근성이 낮음",
                      "주말·공휴일 포함 일정으로 조정", gain))
    if plan.month in (1, 2, 7, 12):
        fb.append(_fb("비수기/기상 리스크 시기",
                      "혹한·혹서·장마 시기 개최는 방문 저하 위험",
                      "봄(4~5월)·가을(9~10월) 성수기로 일정 이동 검토", None))
    if not plan.near_holiday:
        fb.append(_fb("연휴 미활용",
                      "연휴·황금연휴와 연계되지 않아 방문 유인이 약함",
                      "인접 공휴일·징검다리 연휴에 맞춰 일정 배치", None))
    if plan.nature_peak_match < 0.7:
        fb.append(_fb("자연물 절정 시기 불일치",
                      f"개화/단풍 등 절정 일치도 {plan.nature_peak_match:.0%} — 시기 어긋남",
                      "그 해 개화/단풍 예보에 맞춰 개최일 미세 조정", None))

    # 프로그램 약점
    if f["program"] < 60:
        missing = []
        if not plan.has_experience:
            missing.append("체험형 프로그램")
        if not plan.has_food:
            missing.append("먹거리")
        if not plan.has_performance:
            missing.append("공연/무대")
        if not plan.has_celebrity:
            missing.append("유명 아티스트 라인업")
        if missing:
            fb.append(_fb("프로그램 빈약", f"부족 요소: {', '.join(missing)}",
                          f"{missing[0]} 우선 보강 — 체류시간·재방문 유도", None))
    if not plan.is_free:
        fb.append(_fb("입장료 진입장벽",
                      "유료 입장은 초기 방문 유인을 낮춤",
                      "무료화 또는 사전예매 할인·패키지로 진입장벽 완화", None))

    # 수요·접근성 약점
    if f["demand"] < 50:
        fb.append(_fb("주변 수요 부족",
                      f"주변 인구 {demo.total_population:,}명·접근성 낮음",
                      "인근 도시 광역 홍보 + 관광버스/셔틀 연계로 도달 범위 확대", None))
    if region.nearby_festivals_same_week >= 2:
        fb.append(_fb("경쟁 축제 밀집",
                      f"같은 주말 인근 축제 {region.nearby_festivals_same_week}건 — 관객 분산",
                      "개최 주말을 1~2주 분산하거나 차별화 콘텐츠로 포지셔닝", None))
    if not region.has_shuttle and region.distance_to_station_km > 5:
        fb.append(_fb("대중교통 접근성",
                      f"역/터미널까지 {region.distance_to_station_km}km, 셔틀 없음",
                      "역-행사장 셔틀버스 운영으로 무자차 방문객 확보", None))

    # 평판·홍보 약점
    if plan.festival_grade == "none":
        fb.append(_fb("지정축제 미선정",
                      "문체부 문화관광축제 지정 이력 없음 — 공신력·홍보력 약함",
                      "문화관광축제 지정 신청 요건 정비(콘텐츠·안전·데이터 관리)", None))
    if plan.preorders == 0 or plan.promo_channels < 2:
        fb.append(_fb("홍보 투입 부족",
                      "사전예매/홍보 채널이 적어 초기 확산이 어려움",
                      "사전예매 오픈 + SNS·지역채널 등 홍보 채널 다변화", None))

    # 외국인 유치 기회 (K콘텐츠 미연계 시)
    if not plan.has_kcontent:
        split = estimate_visitor_split(plan, demo, result["score"], macro)
        eff = split["kcontent_effect"]
        fb.append(_fb("외국인 유치 기회 미활용",
                      f"현재 예상 외국인 {split['foreign']:,}명 — K콘텐츠 미연계",
                      "인근 드라마 촬영지·K팝/한류 콘텐츠 연계(포토존·투어·굿즈) "
                      "+ 외국어 안내·다국어 SNS 홍보",
                      None,
                      extra={"expected_foreign_uplift":
                             f"외국인 약 {eff['delta']:,}명 추가 (+{eff['uplift_pct']:.0f}%) 기대"}))

    return fb


# ────────────────────────────────────────────────────────────
# ③ 마케팅 / 타깃 추천 (주변 인구 기반)
# ────────────────────────────────────────────────────────────
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
                 wx: WeatherOutlook, region: RegionContext | None = None,
                 macro: MacroContext | None = None,
                 capacity: int | None = None) -> dict:
    """흥행 예보 리포트 전체를 조립한다."""
    region = region or RegionContext()
    macro = macro or MacroContext()
    appeal = appeal_score(plan, demo, wx, region)
    return {
        "festival": plan.name,
        "region": plan.region,
        "appeal_score": appeal["score"],
        "grade": _grade(appeal["score"]),
        "factor_breakdown": appeal["factors"],
        "visitors": estimate_visitor_split(plan, demo, appeal["score"], macro),
        "visitor_forecast": forecast_distribution(plan, demo, wx, region, macro,
                                                  capacity=capacity),
        "feedback": generate_feedback(plan, demo, wx, region, macro),
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
        has_performance=True, has_celebrity=False, duration_days=2,
        is_free=True, budget_manwon=30000,
        has_kcontent=False, near_intl_gateway=False,
        near_holiday=False, during_vacation=True, nature_peak_match=0.5,
        festival_grade="none", prev_visitors=2800, num_editions=3,
        promo_budget_manwon=1500, promo_channels=1, preorders=0,
    )
    demo = RegionDemographics(
        total_population=120_000,
        age_counts={"10s": 9000, "20s": 14000, "30s": 22000,
                    "40s": 26000, "50s": 21000, "60s+": 28000},
        female_ratio=0.54,
    )
    region = RegionContext(
        distance_to_seoul_km=70, distance_to_station_km=8,
        has_shuttle=False, parking_capacity=300,
        nearby_festivals_same_week=2, lodging_count=40, restaurant_count=200,
    )
    macro = MacroContext(exchange_rate_krw_usd=1380, pandemic_index=0.0)
    wx = WeatherOutlook(avg_temp_c=29.0, rain_prob=0.6)

    report = build_report(plan, demo, wx, region, macro, capacity=4000)
    print("=== 흥행 예보 리포트 ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    fc = report["visitor_forecast"]
    print("\n=== 방문자 확률 예보 (100명 단위) ===")
    print(f"기대값 {fc['expected']:,}명 · 80% 구간 "
          f"{fc['interval_80'][0]:,}~{fc['interval_80'][1]:,}명")
    for b in fc["buckets"]:
        bar = "█" * int(b["prob_pct"] / 2)
        print(f"  {b['range']:>16}  {b['prob_pct']:>5.1f}%  {bar}")
    print(f"\n수용인원 {fc['capacity']:,}명 초과(쏠림) 확률: "
          f"{fc['overcrowding_prob_pct']}%  → 위험도 {fc['overcrowding_risk']}")


if __name__ == "__main__":
    _demo()
