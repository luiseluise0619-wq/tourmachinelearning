"""실측 축제 레코드 → FestCast 엔진 입력(FestivalPlan) 매퍼.

문체부 시드에는 있는 값(일정·기간·예산·회차·유형)은 실측으로 채우고,
아직 조인 전인 값(날씨·주변인구)은 근사치로 채워 엔진을 실제 축제에 돌린다.
  · 날씨: 개최 월의 전국 평년 기후(climatology) — 추후 기상청 지점별로 교체
  · 주변 인구: 시도 인구 프록시 + 전국 연령 분포 — 추후 주민등록 인구로 교체

사용:
    python -m src.festival_to_plan "머드"        # 이름에 '머드' 들어간 축제 리포트
    python -m src.festival_to_plan "산천어" --capacity 20000
"""
from __future__ import annotations

import argparse
import datetime as dt

from src.load_festivals import FestivalRecord, load_festivals
from src.scoring import (
    FestivalPlan,
    MacroContext,
    RegionContext,
    RegionDemographics,
    WeatherOutlook,
    build_report,
)

# 개최 월별 전국 평년 기후 (근사) — (평균기온℃, 강수확률)
_CLIMATOLOGY = {
    1: (-1, 0.15), 2: (2, 0.18), 3: (7, 0.22), 4: (13, 0.25),
    5: (18, 0.28), 6: (22, 0.40), 7: (25, 0.55), 8: (26, 0.50),
    9: (21, 0.35), 10: (15, 0.22), 11: (8, 0.20), 12: (1, 0.16),
}

# 시도 인구 프록시(명, 근사) — 주변 수요 베이스라인 (추후 주민등록 인구로 교체)
_REGION_POP = {
    "서울": 9_400_000, "부산": 3_300_000, "대구": 2_370_000, "인천": 3_000_000,
    "광주": 1_420_000, "대전": 1_440_000, "울산": 1_100_000, "세종": 390_000,
    "경기": 13_600_000, "강원": 1_520_000, "충북": 1_590_000, "충남": 2_130_000,
    "전북": 1_750_000, "전남": 1_800_000, "경북": 2_550_000, "경남": 3_250_000,
    "제주": 670_000,
}

# 전국 연령 분포(10세 이상 근사 비율)
_AGE_SHARE = {"10s": 0.10, "20s": 0.13, "30s": 0.14, "40s": 0.16, "50s": 0.17, "60s+": 0.30}

_OUTDOOR_TYPES = {"녹지형", "수변형", "마을형", "자연생태"}
_INTL_GATEWAY_REGIONS = {"서울", "인천", "부산", "제주"}


def _includes_weekend(start: str | None, end: str | None) -> bool:
    if not start:
        return False
    s = dt.date.fromisoformat(start)
    e = dt.date.fromisoformat(end) if end else s
    for i in range((e - s).days + 1):
        if (s + dt.timedelta(days=i)).weekday() >= 5:   # 5=토, 6=일
            return True
    return False


def to_plan(rec: FestivalRecord) -> tuple[FestivalPlan, RegionDemographics,
                                          WeatherOutlook, RegionContext, MacroContext]:
    """실측 레코드를 엔진 입력 5종으로 변환한다."""
    month = rec.month or 5
    temp, rain = _CLIMATOLOGY.get(month, (18, 0.3))

    cat = rec.category or ""
    plan = FestivalPlan(
        name=rec.title,
        region=rec.region or "미상",
        month=month,
        is_outdoor=(rec.venue_type in _OUTDOOR_TYPES) if rec.venue_type else True,
        is_weekend=_includes_weekend(rec.start_date, rec.end_date),
        num_programs=5,                                   # 세부 프로그램 미상 → 기본
        has_experience="체험" in cat,
        has_food=any(k in cat for k in ("특산", "먹거리", "음식")),
        has_performance=("문화예술" in cat or "공연" in cat),
        has_celebrity=False,
        duration_days=rec.duration_days or 2,
        is_free=True,
        budget_manwon=int((rec.budget_mil_won or 0) * 100),   # 백만원 → 만원
        has_kcontent=False,
        near_intl_gateway=(rec.region in _INTL_GATEWAY_REGIONS),
        near_holiday=False,
        during_vacation=month in (1, 2, 7, 8),
        nature_peak_match=1.0,
        festival_grade="none",
        prev_visitors=rec.visitors_total,                 # 전년 실측
        num_editions=rec.num_editions or 1,
        promo_budget_manwon=0,
        promo_channels=1,
        preorders=0,
    )

    pop = _REGION_POP.get(rec.region or "", 1_000_000)
    demo = RegionDemographics(
        total_population=pop,
        age_counts={k: int(pop * v) for k, v in _AGE_SHARE.items()},
        female_ratio=0.50,
    )
    wx = WeatherOutlook(avg_temp_c=temp, rain_prob=rain)
    region = RegionContext(
        distance_to_seoul_km=30 if rec.region in ("서울", "경기", "인천") else 150,
        distance_to_station_km=5, has_shuttle=False, parking_capacity=500,
        nearby_festivals_same_week=1, lodging_count=50, restaurant_count=300,
    )
    macro = MacroContext(exchange_rate_krw_usd=1380, pandemic_index=0.0)
    return plan, demo, wx, region, macro


def main() -> None:
    parser = argparse.ArgumentParser(description="실측 축제 → FestCast 리포트")
    parser.add_argument("query", help="축제명 일부")
    parser.add_argument("--capacity", type=int, default=None, help="수용인원(쏠림 위험용)")
    args = parser.parse_args()

    recs = [r for r in load_festivals() if args.query in r.title]
    if not recs:
        print(f"'{args.query}' 포함 축제를 찾지 못했습니다.")
        return
    rec = max(recs, key=lambda r: r.visitors_total or 0)   # 가장 큰 축제 선택

    plan, demo, wx, region, macro = to_plan(rec)
    report = build_report(plan, demo, wx, region, macro, capacity=args.capacity)

    print(f"=== {rec.title} ({rec.region}, {rec.start_date}) ===")
    print(f"실측 전년 방문객: {rec.visitors_total:,}명 "
          f"(내국 {rec.visitors_domestic or 0:,} / 외국 {rec.visitors_foreign or 0:,})")
    print(f"예산: {rec.budget_mil_won:,.0f}백만원 · {rec.num_editions}회차 · {rec.duration_days}일")
    print(f"\n[FestCast 예측]")
    print(f"흥행도: {report['appeal_score']}점 ({report['grade']})")
    print(f"요인: {report['factor_breakdown']}")
    v = report["visitors"]
    print(f"예상 방문객: {v['total']:,}명 (내국 {v['domestic']:,} / 외국 {v['foreign']:,})")
    fc = report["visitor_forecast"]
    print(f"확률 예보: 80% 구간 {fc['interval_80'][0]:,}~{fc['interval_80'][1]:,}명")
    if "overcrowding_prob_pct" in fc:
        print(f"쏠림 위험(수용 {fc['capacity']:,}명 초과): {fc['overcrowding_prob_pct']}% "
              f"({fc['overcrowding_risk']})")
    print(f"\n[보완 피드백 {len(report['feedback'])}건]")
    for f in report["feedback"][:6]:
        print(f"  • {f['issue']}: {f['action']}")
    m = report["marketing"]
    print(f"\n[마케팅] 타깃 {m['primary_segment']} · 채널 {', '.join(m['recommended_channels'])}")


if __name__ == "__main__":
    main()
