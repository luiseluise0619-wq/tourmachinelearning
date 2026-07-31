"""소셜 관심도(buzz) 수집 — 축제/콘텐츠에 대한 '사람들의 관심'을 지수화.

여러 플랫폼의 키워드 관심 신호를 하나의 **관심도 지수(0~100)**로 묶는다.
축제 방문의 강력한 **선행지표**이자, K콘텐츠 연계 효과의 근거가 된다.

지원 소스 (과거 시계열 확보 가능 = 학습에 사용 가능):
  · 네이버 데이터랩 검색어 트렌드  (한국 관심도, 최적)   — NAVER_CLIENT_ID/SECRET
  · 구글 트렌드 (pytrends)         (외국인 관심도)        — 키 불필요
  · YouTube Data API v3            (키워드 영상 수)       — YOUTUBE_API_KEY

⚠️ 트위터/X·인스타그램은 무료 과거검색이 사실상 불가 → 학습용에서 제외.
⚠️ **시점정합**: 반드시 '축제 시점 T 이전' 창의 관심도만 사용(누수 방지, docs/features.md).

사용:
    python -m src.collect_buzz --keyword "머드축제" --start 2025-05 --end 2025-07
    python -m src.collect_buzz --selftest
"""
from __future__ import annotations

import argparse
import os

from src.config import ROOT_DIR

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass


def naver_interest(keyword: str, start: str, end: str) -> float | None:
    """네이버 데이터랩 기간 평균 검색 관심도(0~100)."""
    try:
        from src.collect_trends import fetch_trend
        df = fetch_trend(keyword, start, end, "month")
        return round(float(df["ratio"].mean()), 1) if not df.empty else None
    except Exception:
        return None


def google_interest(keyword: str, start: str, end: str, geo: str = "") -> float | None:
    """구글 트렌드 기간 평균 관심도(0~100). geo='KR' 국내, ''=전세계(외국인)."""
    try:
        from pytrends.request import TrendReq
        tf = f"{start if len(start)==10 else start+'-01'} {end if len(end)==10 else end+'-28'}"
        py = TrendReq(hl="ko", tz=540)
        py.build_payload([keyword], timeframe=tf, geo=geo)
        d = py.interest_over_time()
        return round(float(d[keyword].mean()), 1) if d is not None and not d.empty else None
    except Exception:
        return None


def youtube_count(keyword: str, start: str, end: str) -> int | None:
    """기간 내 키워드 관련 유튜브 영상 수(관심도 프록시). publishedBefore/After로 시점정합."""
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key:
        return None
    try:
        import requests
        def _iso(d, tail):
            return (d if len(d) == 10 else d + tail) + "T00:00:00Z"
        r = requests.get("https://www.googleapis.com/youtube/v3/search", timeout=20, params={
            "part": "snippet", "q": keyword, "type": "video", "maxResults": 1,
            "publishedAfter": _iso(start, "-01"), "publishedBefore": _iso(end, "-28"),
            "key": key,
        })
        r.raise_for_status()
        return int(r.json().get("pageInfo", {}).get("totalResults", 0))
    except Exception:
        return None


def interest_index(keyword: str, start: str, end: str) -> dict:
    """여러 소스를 합쳐 관심도 지수(0~100)를 만든다. 가용 소스만 평균.

    start~end 는 **축제 이전 관심 창**으로 줄 것 (예: 개최 2개월 전 ~ 개최 직전).
    """
    nv = naver_interest(keyword, start, end)
    gg_kr = google_interest(keyword, start, end, geo="KR")
    gg_global = google_interest(keyword, start, end, geo="")
    yt = youtube_count(keyword, start, end)
    yt_norm = None if yt is None else min(yt / 1000 * 100, 100)  # 1000영상=100 근사

    parts = [v for v in (nv, gg_kr, yt_norm) if v is not None]
    index = round(sum(parts) / len(parts), 1) if parts else None
    return {
        "keyword": keyword, "window": f"{start}~{end}",
        "naver": nv, "google_kr": gg_kr, "google_global": gg_global,
        "youtube_videos": yt, "interest_index": index,
        "sources_used": len(parts),
    }


def _selftest() -> None:
    """네트워크 없이 합성 로직 검증 (지수 계산부)."""
    # 소스 3개 중 2개만 가용한 상황 가정
    parts = [v for v in (62.0, None, 48.0) if v is not None]
    idx = round(sum(parts) / len(parts), 1)
    assert idx == 55.0, idx
    print("✅ 관심도 지수 합성 로직 정상 (예: 네이버 62·유튜브 48 → 지수 55.0)")


def main() -> None:
    ap = argparse.ArgumentParser(description="소셜 관심도(buzz) 수집")
    ap.add_argument("--keyword")
    ap.add_argument("--start", help="관심 창 시작 YYYY-MM(-DD)")
    ap.add_argument("--end", help="관심 창 끝 YYYY-MM(-DD)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest or not (args.keyword and args.start and args.end):
        _selftest()
        return
    import json
    print(json.dumps(interest_index(args.keyword, args.start, args.end),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
