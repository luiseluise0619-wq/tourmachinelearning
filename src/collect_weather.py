"""기상청 지상(종관, ASOS) 일자료 수집 — 날씨 핵심 피처.

기상청 API 허브 / 공공데이터포털의 "기상청_지상(종관, ASOS) 일자료 조회서비스"
(getWthrDataList) 를 사용한다. 축제 개최일의 기온·강수량 등을 붙여
"날씨 → 방문자수" 가설을 검증할 피처로 쓴다.

- 발급: 공공데이터포털 → "기상청_지상(종관, ASOS) 일자료 조회서비스"
- 주요 지점번호(stnIds) 예: 서울 108, 부산 159, 대구 143, 광주 156, 제주 184

사용 예:
    python -m src.collect_weather --stn 108 --start 20250101 --end 20251231
"""
from __future__ import annotations

import argparse
import time

import pandas as pd
import requests

from src.config import KMA_SERVICE_KEY, RAW_DIR, require_key

BASE_URL = (
    "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
)


def fetch_daily_weather(stn_id: str, start: str, end: str,
                        num_rows: int = 999, max_pages: int = 50) -> pd.DataFrame:
    """지점·기간의 일별 관측값을 수집한다.

    Args:
        stn_id: 관측 지점번호 (예: 서울 108).
        start:  시작일 YYYYMMDD.
        end:    종료일 YYYYMMDD.
    """
    key = require_key("KMA_SERVICE_KEY", KMA_SERVICE_KEY)
    rows: list[dict] = []

    for page in range(1, max_pages + 1):
        params = {
            "serviceKey": key,
            "dataType": "JSON",
            "dataCd": "ASOS",
            "dateCd": "DAY",
            "startDt": start,
            "endDt": end,
            "stnIds": stn_id,
            "numOfRows": num_rows,
            "pageNo": page,
        }
        resp = requests.get(BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()

        body = payload.get("response", {}).get("body", {})
        items = body.get("items")
        if not items or items in ("", None):
            break

        page_items = items["item"]
        if isinstance(page_items, dict):
            page_items = [page_items]
        rows.extend(page_items)

        total = int(body.get("totalCount", 0))
        if page * num_rows >= total:
            break
        time.sleep(0.2)

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="기상청 ASOS 일자료 수집")
    parser.add_argument("--stn", required=True, help="관측 지점번호 (예: 108)")
    parser.add_argument("--start", required=True, help="시작일 YYYYMMDD")
    parser.add_argument("--end", required=True, help="종료일 YYYYMMDD")
    parser.add_argument("--out", default=None, help="저장 파일명")
    args = parser.parse_args()

    df = fetch_daily_weather(args.stn, args.start, args.end)
    out_name = args.out or f"weather_{args.stn}_{args.start}_{args.end}.csv"
    out_path = RAW_DIR / out_name
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"수집 완료: {len(df)}건 → {out_path}")


if __name__ == "__main__":
    main()
