"""한국관광공사 TourAPI 축제/행사 정보 수집 (필수 API).

축제 정보 조회는 TourAPI(국문 관광정보) 의 `searchFestival` 오퍼레이션을 사용한다.
- 엔드포인트 베이스: http://apis.data.go.kr/B551011/KorService2
- 발급: 공공데이터포털(data.go.kr) → "한국관광공사_국문 관광정보 서비스"

사용 예:
    python -m src.collect_tourapi --start 20260101 --end 20261231
"""
from __future__ import annotations

import argparse
import time

import pandas as pd
import requests

from src.config import RAW_DIR, TOURAPI_SERVICE_KEY, require_key

BASE_URL = "http://apis.data.go.kr/B551011/KorService2/searchFestival2"


def fetch_festivals(event_start: str, event_end: str | None = None,
                    num_rows: int = 100, max_pages: int = 50) -> pd.DataFrame:
    """기간 내 개최 축제 목록을 페이지네이션으로 모두 수집한다.

    Args:
        event_start: 행사 시작일 (YYYYMMDD). 이 날짜 이후 개최 축제 조회.
        event_end:   행사 종료일 (YYYYMMDD, 선택).
        num_rows:    페이지당 건수.
        max_pages:   안전장치용 최대 페이지 수.
    """
    key = require_key("TOURAPI_SERVICE_KEY", TOURAPI_SERVICE_KEY)
    rows: list[dict] = []

    for page in range(1, max_pages + 1):
        params = {
            "serviceKey": key,
            "MobileOS": "ETC",
            "MobileApp": "FestCast",
            "_type": "json",
            "arrange": "A",           # 제목순
            "eventStartDate": event_start,
            "numOfRows": num_rows,
            "pageNo": page,
        }
        if event_end:
            params["eventEndDate"] = event_end

        resp = requests.get(BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()

        body = payload.get("response", {}).get("body", {})
        items = body.get("items")
        if not items or items in ("", None):
            break

        page_items = items["item"]
        if isinstance(page_items, dict):   # 단건이면 dict 로 옴
            page_items = [page_items]
        rows.extend(page_items)

        total = int(body.get("totalCount", 0))
        if page * num_rows >= total:
            break
        time.sleep(0.2)   # API 예의상 살짝 텀

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="TourAPI 축제 정보 수집")
    parser.add_argument("--start", required=True, help="행사 시작일 YYYYMMDD")
    parser.add_argument("--end", default=None, help="행사 종료일 YYYYMMDD (선택)")
    parser.add_argument("--out", default=None, help="저장 파일명 (기본: festivals_<start>.csv)")
    args = parser.parse_args()

    df = fetch_festivals(args.start, args.end)
    out_name = args.out or f"festivals_{args.start}.csv"
    out_path = RAW_DIR / out_name
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"수집 완료: {len(df)}건 → {out_path}")


if __name__ == "__main__":
    main()
