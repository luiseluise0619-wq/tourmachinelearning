"""네이버 데이터랩 검색어 트렌드 수집 — K콘텐츠 인기도(시점별).

축제 인근 연계 콘텐츠(드라마·K팝·한류스타 등)가 **그 시점에** 얼마나 핫했는지를
검색량 추이로 측정한다. FestCast 의 K콘텐츠 피처는 반드시 '축제 날짜 T 기준'
검색량이어야 누수(hindsight)를 피한다(docs/features.md 참고).

- 발급: 네이버 개발자센터 https://developers.naver.com → 애플리케이션 등록 →
  '데이터랩(검색어 트렌드)' 사용 → Client ID / Secret
- .env 에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 추가

사용:
    python -m src.collect_trends --keyword "오징어게임" --start 2021-08 --end 2021-12
"""
from __future__ import annotations

import argparse
import json
import os

import pandas as pd
import requests

from src.config import RAW_DIR, ROOT_DIR

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

API_URL = "https://openapi.naver.com/v1/datalab/search"


def fetch_trend(keyword: str, start: str, end: str,
                time_unit: str = "month") -> pd.DataFrame:
    """키워드의 기간별 상대 검색량(0~100)을 조회한다.

    Args:
        keyword: 검색 키워드(연계 콘텐츠명).
        start:   시작일 'YYYY-MM-DD' 또는 'YYYY-MM'(-01 보정).
        end:     종료일.
        time_unit: date/week/month.
    """
    cid = os.getenv("NAVER_CLIENT_ID", "")
    csec = os.getenv("NAVER_CLIENT_SECRET", "")
    if not cid or not csec:
        raise RuntimeError(
            "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 미설정. "
            ".env 에 네이버 데이터랩 키를 추가하세요."
        )

    def _norm(d: str) -> str:
        return d if len(d) == 10 else f"{d}-01"

    body = {
        "startDate": _norm(start),
        "endDate": _norm(end),
        "timeUnit": time_unit,
        "keywordGroups": [{"groupName": keyword, "keywords": [keyword]}],
    }
    headers = {
        "X-Naver-Client-Id": cid,
        "X-Naver-Client-Secret": csec,
        "Content-Type": "application/json",
    }
    resp = requests.post(API_URL, data=json.dumps(body), headers=headers, timeout=20)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return pd.DataFrame(columns=["period", "ratio"])
    df = pd.DataFrame(results[0]["data"])
    df["keyword"] = keyword
    return df.rename(columns={"period": "period", "ratio": "ratio"})


def main() -> None:
    parser = argparse.ArgumentParser(description="네이버 데이터랩 검색어 트렌드 수집")
    parser.add_argument("--keyword", required=True, help="연계 콘텐츠 키워드")
    parser.add_argument("--start", required=True, help="시작 YYYY-MM(-DD)")
    parser.add_argument("--end", required=True, help="종료 YYYY-MM(-DD)")
    parser.add_argument("--unit", default="month", choices=["date", "week", "month"])
    args = parser.parse_args()

    df = fetch_trend(args.keyword, args.start, args.end, args.unit)
    out_path = RAW_DIR / f"trend_{args.keyword}_{args.start}_{args.end}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"수집 완료: {len(df)}행 → {out_path}")
    if not df.empty:
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
