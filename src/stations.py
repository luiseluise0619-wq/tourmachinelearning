"""축제 개최지 → 기상청 ASOS 관측지점 매핑.

날씨 데이터를 붙이려면 각 축제의 지역을 가장 가까운 종관기상관측(ASOS) 지점에
연결해야 한다. 지점번호는 고정값이라 API 키 없이 미리 만들어 둔다.
(대표 지점 근사 — 필요 시 시군구별로 정밀화 가능)
"""
from __future__ import annotations

# 시도 → 대표 ASOS 지점번호
SIDO_STATION = {
    "서울": 108, "부산": 159, "대구": 143, "인천": 112, "광주": 156,
    "대전": 133, "울산": 152, "세종": 133, "경기": 119, "강원": 105,
    "충북": 131, "충남": 129, "전북": 146, "전남": 165, "경북": 136,
    "경남": 155, "제주": 184,
}

# 주요 축제 개최 시군구 → 더 가까운 지점 (대표 지점보다 정확)
SIGUNGU_STATION = {
    "화천": 101, "춘천": 101, "강릉": 105, "속초": 90, "원주": 114,
    "보령": 235, "서산": 129, "천안": 232, "포항": 138, "경주": 138,
    "안동": 136, "여수": 168, "순천": 174, "목포": 165, "통영": 162,
    "진주": 192, "창원": 155, "김해": 253, "전주": 146, "군산": 140,
    "제천": 221, "충주": 127, "태백": 216, "정선": 217, "부여": 236,
}


def resolve_station(region: str | None, sigungu: str | None) -> int | None:
    """지역명으로 ASOS 지점번호를 반환. 시군구 우선, 없으면 시도 대표."""
    if sigungu:
        for key, stn in SIGUNGU_STATION.items():
            if key in sigungu:
                return stn
    if region:
        for name, stn in SIDO_STATION.items():
            if region.startswith(name) or name in region:
                return stn
    return None
