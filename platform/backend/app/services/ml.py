"""AI 서비스 — 기존 FestCast 엔진(../../src) 재사용.

방문객 예측·성공확률·영향변수·보완피드백·마케팅을 서빙한다.
레포 루트를 sys.path에 추가해 `src.scoring` 등을 그대로 import.
"""
from __future__ import annotations

import datetime as dt
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]   # repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scoring import (FestivalPlan, MacroContext, RegionContext,  # noqa: E402
                         RegionDemographics, WeatherOutlook, build_report)

# festival_to_plan의 상수 재사용
try:
    from src.festival_to_plan import (_AGE_SHARE, _CLIMATOLOGY,  # noqa: E402
                                      _INTL_GATEWAY_REGIONS, _OUTDOOR_TYPES,
                                      _REGION_POP)
except Exception:  # pragma: no cover
    _CLIMATOLOGY = {m: (18, 0.3) for m in range(1, 13)}
    _REGION_POP = {}
    _AGE_SHARE = {"20s": 0.2, "30s": 0.2, "40s": 0.2, "50s": 0.2, "60s+": 0.2}
    _OUTDOOR_TYPES, _INTL_GATEWAY_REGIONS = set(), {"서울", "인천", "부산", "제주"}


def _includes_weekend(start: str | None, end: str | None) -> bool:
    try:
        s = dt.date.fromisoformat(start)
        e = dt.date.fromisoformat(end) if end else s
        return any((s + dt.timedelta(days=i)).weekday() >= 5
                   for i in range((e - s).days + 1))
    except Exception:
        return True


def map_to_engine(f: dict):
    """플랫폼 축제 dict → 엔진 입력 5종."""
    start = f.get("start_date")
    month = int(start[5:7]) if start and len(start) >= 7 else 5
    temp, rain = _CLIMATOLOGY.get(month, (18, 0.3))
    wx_over = f.get("weather") or {}
    content = f.get("content") or {}
    region = f.get("region") or "경기"

    plan = FestivalPlan(
        name=f.get("name", "축제"), region=region, month=month,
        is_outdoor=bool((f.get("basic") or {}).get("is_outdoor", True)),
        is_weekend=_includes_weekend(start, f.get("end_date")),
        num_programs=int(content.get("num_programs", 5) or 5),
        has_experience=bool(content.get("experience")),
        has_food=bool(content.get("food")),
        has_performance=bool(content.get("performance")),
        has_celebrity=bool(content.get("celebrity")),
        duration_days=int(f.get("duration_days") or 2),
        is_free=bool(f.get("is_free", True)),
        budget_manwon=int((f.get("budget_mil_won") or 0) * 100),
        has_kcontent=bool(content.get("kcontent")),
        near_intl_gateway=region in _INTL_GATEWAY_REGIONS,
        during_vacation=month in (1, 2, 7, 8),
        prev_visitors=f.get("visitors_total") or None,
        num_editions=int((f.get("basic") or {}).get("num_editions", 1) or 1),
        promo_budget_manwon=int((f.get("basic") or {}).get("promo_budget_manwon", 0) or 0),
    )
    pop = _REGION_POP.get(region, 1_000_000)
    demo = RegionDemographics(
        total_population=int((f.get("region_data") or {}).get("population", pop) or pop),
        age_counts={k: int(pop * v) for k, v in _AGE_SHARE.items()},
        female_ratio=0.5,
    )
    wx = WeatherOutlook(
        avg_temp_c=float(wx_over.get("avg_temp", temp)),
        rain_prob=float(wx_over.get("rain_prob", rain)),
    )
    acc = f.get("access") or {}
    region_ctx = RegionContext(
        distance_to_seoul_km=float(acc.get("distance_to_seoul_km",
                                           30 if region in ("서울", "경기", "인천") else 150)),
        distance_to_station_km=float(acc.get("distance_to_station_km", 5)),
        has_shuttle=bool(acc.get("has_shuttle", False)),
        parking_capacity=int(acc.get("parking_capacity", 300) or 0),
        nearby_festivals_same_week=int((f.get("operations") or {}).get("nearby_festivals", 1) or 0),
        lodging_count=int(acc.get("lodging_count", 40) or 0),
        restaurant_count=int(acc.get("restaurant_count", 200) or 0),
    )
    macro = MacroContext()
    capacity = (f.get("operations") or {}).get("capacity")
    return plan, demo, wx, region_ctx, macro, (int(capacity) if capacity else None)


def _success_prob(score: float) -> float:
    """흥행도 점수 → 성공 확률(로지스틱 근사, 60점=성공 기준)."""
    import math
    return round(1 / (1 + math.exp(-(score - 60) / 12)), 3)


def predict(f: dict) -> dict:
    """방문객 예측 + 신뢰구간 + 성공확률 + 영향변수 + 피드백 + 마케팅."""
    plan, demo, wx, region_ctx, macro, capacity = map_to_engine(f)
    report = build_report(plan, demo, wx, region_ctx, macro, capacity=capacity)
    fc = report["visitor_forecast"]
    factors = report["factor_breakdown"]
    top = sorted(factors.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "expected_visitors": report["visitors"]["total"],
        "domestic": report["visitors"]["domestic"],
        "foreign": report["visitors"]["foreign"],
        "interval_80": fc["interval_80"],
        "distribution": fc["buckets"],
        "appeal_score": report["appeal_score"],
        "grade": report["grade"],
        "success_probability": _success_prob(report["appeal_score"]),
        "top_factors": [{"factor": k, "score": v} for k, v in top],
        "overcrowding": {"prob_pct": fc.get("overcrowding_prob_pct"),
                         "risk": fc.get("overcrowding_risk"),
                         "capacity": fc.get("capacity")},
        "feedback": report["feedback"],
        "marketing": report["marketing"],
        "kcontent_effect": report["visitors"]["kcontent_effect"],
    }


def success_analysis(f: dict) -> dict:
    """성공 가능성 점수 + 실패 위험요소 + 개선추천."""
    p = predict(f)
    risks = [{"issue": x["issue"], "why": x.get("diagnosis", ""), "action": x["action"]}
             for x in p["feedback"]]
    weak = [t["factor"] for t in p["top_factors"] if t["score"] < 55]
    return {
        "success_score": p["appeal_score"],
        "success_probability": p["success_probability"],
        "grade": p["grade"],
        "weak_factors": weak,
        "risks": risks,
        "recommendations": [r["action"] for r in risks[:5]],
    }


@lru_cache(maxsize=1)
def model_comparison() -> dict:
    """XGBoost/RF/GBM 등 교차검증 R² 비교 + 영향변수 (1회 캐시)."""
    try:
        from src.model import _design, build_frame
        from src.model_best import compare_models
        df = build_frame()
        X, y = _design(df)
        scores, _ = compare_models(X, y)
        # 영향변수(전역 중요도) — RF로 간이 산출
        from sklearn.ensemble import RandomForestRegressor
        rf = RandomForestRegressor(n_estimators=200, max_depth=8,
                                   min_samples_leaf=5, random_state=0, n_jobs=-1).fit(X, y)
        import pandas as pd
        imp = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
        return {
            "cv_r2": {k: round(v, 3) for k, v in scores.items()},
            "best": max(scores, key=scores.get),
            "top_features": [{"feature": i, "importance": round(float(v), 3)}
                             for i, v in imp.head(10).items()],
            "samples": int(len(X)),
        }
    except Exception as exc:  # pragma: no cover
        return {"error": f"모델 비교 불가(데이터 확인): {exc}"}
