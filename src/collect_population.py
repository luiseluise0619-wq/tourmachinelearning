"""주변 지역 연령대·성별 인구 수집 — 수요 예측 + 마케팅 타깃의 근거 데이터.

축제 개최지 주변의 연령대별 인구 규모는 (1) 방문자 수요의 베이스라인이자
(2) 홍보 타깃/채널을 정하는 근거가 된다(docs/architecture.md §3).

데이터 소스 (공공데이터포털 https://www.data.go.kr):
  · "행정안전부_지역별(법정동) 성별 연령별 주민등록 인구수" 계열 서비스
  · 또는 KOSIS(통계청) 연령별 인구. 실제 사용할 데이터셋의 오퍼레이션/파라미터명은
    발급 화면에서 확인해 아래 PARAM 매핑만 맞추면 된다.

이 스크립트는 공공 API 응답(행정구역별 연령대 인구)을 FestCast 엔진이 쓰는
연령대 버킷('10s'~'60s+')으로 정규화하는 데 초점을 둔다.

사용 예:
    python -m src.collect_population --region "경기도 수원시"
    python -m src.collect_population --demo        # 키 없이 정규화 로직만 확인
"""
from __future__ import annotations

import argparse

import pandas as pd
import requests

from src.config import RAW_DIR, TOURAPI_SERVICE_KEY, require_key

# 공공데이터포털 인구통계 서비스 엔드포인트(발급 데이터셋에 맞게 교체).
BASE_URL = "http://apis.data.go.kr/1741000/stdgRgnPpltn/getStdgRgnPpltn"

# FestCast 엔진이 사용하는 연령대 버킷
AGE_BUCKETS = ["10s", "20s", "30s", "40s", "50s", "60s+"]


def _bucket_of(age: int) -> str | None:
    """단일 나이를 엔진 버킷으로 매핑. 10세 미만은 방문 타깃에서 제외."""
    if age < 10:
        return None
    if age >= 60:
        return "60s+"
    return f"{age // 10 * 10}s"


def normalize_age_counts(raw: pd.DataFrame,
                         age_col: str = "age",
                         count_col: str = "population") -> dict[str, int]:
    """(나이, 인구수) 형태의 원본을 엔진 버킷 dict 로 집계한다.

    Args:
        raw:       나이·인구수 컬럼을 가진 DataFrame.
        age_col:   나이(정수) 컬럼명.
        count_col: 인구수 컬럼명.
    """
    counts = {b: 0 for b in AGE_BUCKETS}
    for _, row in raw.iterrows():
        try:
            age = int(row[age_col])
            pop = int(row[count_col])
        except (ValueError, TypeError):
            continue
        b = _bucket_of(age)
        if b:
            counts[b] += pop
    return counts


def fetch_population(region: str, num_rows: int = 1000) -> pd.DataFrame:
    """행정구역명으로 성별·연령별 주민등록 인구를 조회한다.

    실제 파라미터명은 발급받은 데이터셋 문서에 맞춰 조정한다.
    """
    key = require_key("TOURAPI_SERVICE_KEY", TOURAPI_SERVICE_KEY)  # 포털 통합키
    params = {
        "serviceKey": key,
        "type": "JSON",
        "numOfRows": num_rows,
        "pageNo": 1,
        "srchFrYm": "",       # 조회 시작 년월(데이터셋에 따라)
        "admmCd": region,     # 행정구역 코드/명 (데이터셋에 맞게)
    }
    resp = requests.get(BASE_URL, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    # 응답 구조는 데이터셋마다 달라 방어적으로 파싱
    items = (
        payload.get("response", {}).get("body", {}).get("items")
        or payload.get("StdgRgnPpltn", [{}])[-1].get("row")
        or []
    )
    if isinstance(items, dict):
        items = items.get("item", [])
    return pd.DataFrame(items)


def _demo() -> None:
    """키 없이 정규화 로직만 검증 — 가짜 나이별 인구로 버킷 집계 확인."""
    import json
    raw = pd.DataFrame({
        "age": list(range(0, 90)),
        "population": [max(3000 - abs(a - 45) * 30, 200) for a in range(0, 90)],
    })
    counts = normalize_age_counts(raw)
    print("연령대 버킷 집계:")
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    print("총합:", sum(counts.values()))
    print("우세 연령대:", max(counts, key=counts.get))


def main() -> None:
    parser = argparse.ArgumentParser(description="주변 지역 연령대별 인구 수집")
    parser.add_argument("--region", help="행정구역명/코드")
    parser.add_argument("--demo", action="store_true", help="키 없이 정규화 로직 데모")
    parser.add_argument("--out", default=None, help="저장 파일명")
    args = parser.parse_args()

    if args.demo or not args.region:
        _demo()
        return

    raw = fetch_population(args.region)
    out_path = RAW_DIR / (args.out or f"population_{args.region}.csv")
    raw.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"수집 완료: {len(raw)}행 → {out_path}")


if __name__ == "__main__":
    main()
