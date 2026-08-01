"""현실적 샘플 축제 데이터 생성 — 실데이터 확보 전 스키마·데모용.

요구된 전 카테고리(기본·성과·지역·접근성·날씨·콘텐츠·온라인·운영)를 채운다.
실데이터 확보 시 동일 스키마로 교체 가능.
"""
from __future__ import annotations

_SAMPLES = [
    {"name": "한강 별빛 야시장 축제", "region": "서울", "place": "노들섬",
     "start_date": "2026-09-18", "end_date": "2026-09-27", "duration_days": 10,
     "is_free": True, "budget_mil_won": 800, "visitors_total": 420000,
     "audience": "20-30대"},
    {"name": "○○ 가을 국화 축제", "region": "충남", "place": "시민공원",
     "start_date": "2026-10-16", "end_date": "2026-10-25", "duration_days": 10,
     "is_free": True, "budget_mil_won": 320, "visitors_total": 85000,
     "audience": "가족"},
    {"name": "○○ 겨울 빛 페스타", "region": "강원", "place": "호수공원",
     "start_date": "2026-12-19", "end_date": "2027-01-11", "duration_days": 24,
     "is_free": False, "budget_mil_won": 1500, "visitors_total": 260000,
     "audience": "가족·연인"},
]


def make_festival(s: dict) -> dict:
    """샘플 1건을 전 카테고리 dict로 확장."""
    v = s.get("visitors_total", 100000)
    return {
        "name": s["name"], "region": s["region"], "place": s["place"],
        "start_date": s["start_date"], "end_date": s["end_date"],
        "duration_days": s["duration_days"], "is_free": s["is_free"],
        "budget_mil_won": s["budget_mil_won"], "visitors_total": v,
        "basic": {"area_m2": 30000, "hours": "10:00-22:00", "staff": 60,
                  "volunteers": 120, "num_editions": 8, "promo_budget_manwon": 4000,
                  "is_outdoor": True},
        "performance": {"daily_visitors": [int(v/s["duration_days"])]*s["duration_days"],
                        "revenue_mil_won": round(v*0.012, 1), "satisfaction": 4.1,
                        "revisit_rate": 0.34, "sns_mentions": int(v*0.05),
                        "media_exposure": 120},
        "region_data": {"population": 500000, "age_20s_ratio": 0.14,
                        "income_index": 102, "tourists": 320000,
                        "foreign_visitors": int(v*0.03), "card_sales_index": 108},
        "access": {"subway_km": 1.2, "bus_routes": 14, "parking_slots": 800,
                   "distance_to_seoul_km": 10 if s["region"] == "서울" else 130,
                   "distance_to_station_km": 2.0, "has_shuttle": True,
                   "lodging_count": 60, "restaurant_count": 340, "occupancy_rate": 0.72},
        "weather": {"avg_temp": 18, "rain_prob": 0.25, "humidity": 60,
                    "pm10": 45, "wind_ms": 2.1},
        "content": {"num_programs": 12, "performances": ["메인공연", "버스킹"],
                    "headliner_followers": 850000, "experience": True, "food": True,
                    "performance": True, "celebrity": True, "kids": True, "youth": True,
                    "local_specialty": True, "kcontent": False},
        "online": {"search_volume": 74, "sns_mentions": 12000, "hashtags": 8000,
                   "youtube_views": 210000, "blog_reviews": 640, "news_articles": 130,
                   "sentiment": 0.68},
        "operations": {"capacity": int(v*0.7), "nearby_festivals": 1,
                       "restrooms": 40, "waste_ton": 12, "safety_incidents": 1,
                       "police": 20, "fire_staff": 8, "ems_cases": 5},
    }


def sample_festivals() -> list[dict]:
    return [make_festival(s) for s in _SAMPLES]
