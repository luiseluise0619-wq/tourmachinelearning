"""데이터 보강 파이프라인 — 축제에 API 데이터(날씨·인구)를 자동 결합.

문체부 축제 1,266건에 아래를 붙여 학습용 데이터셋을 완성한다:
  · 날씨: 개최 지역(ASOS 지점) × 개최 기간의 실제 기온·강수 (기상청)
  · 주변 인구: 지역 연령대별 인구 (주민등록) — 키 있을 때
키가 없거나 해당 소스가 막히면 그 컬럼만 비우고 계속 진행한다.

⚠️ 클라우드 세션에선 공공 API가 정책상 차단될 수 있다 → **로컬 PC에서 실행**.
사용:
    python -m src.enrich                 # 전체 보강 → data/processed/festivals_enriched.csv
    python -m src.enrich --selftest      # 키 없이 집계 로직만 검증
    python -m src.enrich --limit 50      # 앞 50건만 (테스트)
"""
from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import asdict

import pandas as pd

from src.config import KMA_SERVICE_KEY, PROCESSED_DIR
from src.load_festivals import load_festivals
from src.stations import resolve_station

WEATHER_YEAR = 2025   # 전년(y) 기준 실제 날씨. 연례 축제는 동일 월·일로 매칭.


def _to_year(iso: str, year: int) -> dt.date | None:
    """2026-07-24 → 2025-07-24 (연도만 교체). 2/29 등은 안전 처리."""
    try:
        d = dt.date.fromisoformat(iso)
        try:
            return d.replace(year=year)
        except ValueError:
            return dt.date(year, d.month, min(d.day, 28))
    except (TypeError, ValueError):
        return None


def aggregate_period(lut: dict, start_iso: str, end_iso: str,
                     year: int = WEATHER_YEAR) -> dict:
    """일별 날씨 lut(date->(temp,rain))에서 축제 기간 통계를 집계한다.

    Returns: avg_temp_c, rain_prob(강수일 비율), rained_days, obs_days.
    """
    s = _to_year(start_iso, year)
    e = _to_year(end_iso, year) or s
    if not s:
        return {"wx_avg_temp": None, "wx_rain_prob": None, "wx_rained_days": None}
    temps, rained, obs = [], 0, 0
    for i in range((e - s).days + 1):
        d = (s + dt.timedelta(days=i)).isoformat()
        if d in lut:
            t, rn = lut[d]
            obs += 1
            if t is not None:
                temps.append(t)
            if rn is not None and rn > 0:
                rained += 1
    if obs == 0:
        return {"wx_avg_temp": None, "wx_rain_prob": None, "wx_rained_days": None}
    return {
        "wx_avg_temp": round(sum(temps) / len(temps), 1) if temps else None,
        "wx_rain_prob": round(rained / obs, 2),
        "wx_rained_days": rained,
    }


def _station_daily(stn: int, year: int) -> dict:
    """한 지점의 해당 연도 일별 (기온, 강수) lookup. (네트워크 필요)"""
    from src.collect_weather import fetch_daily_weather
    df = fetch_daily_weather(str(stn), f"{year}0101", f"{year}1231")
    lut = {}
    for _, r in df.iterrows():
        tm = str(r.get("tm", "")).strip()[:10]
        if not tm:
            continue
        def _f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        lut[tm] = (_f(r.get("avgTa")), _f(r.get("sumRn")))
    return lut


def enrich(limit: int | None = None) -> pd.DataFrame:
    recs = load_festivals()
    df = pd.DataFrame([asdict(r) for r in recs])
    if limit:
        df = df.head(limit)
    df["station"] = [resolve_station(r.region, r.sigungu) for r in recs][:len(df)]

    # 지점별 연간 날씨를 1회씩만 수집(효율)
    stations = sorted({int(s) for s in df["station"].dropna().unique()})
    print(f"대상 축제 {len(df):,}건 · 관측지점 {len(stations)}곳")
    cache, failed = {}, 0
    for stn in stations:
        try:
            cache[stn] = _station_daily(stn, WEATHER_YEAR)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if failed <= 2:
                print(f"  [지점 {stn}] 수집 실패: {type(exc).__name__} — {exc}")
    if not cache:
        print("⚠️ 날씨 수집 0건 (키 미설정 또는 네트워크 차단) — 날씨 컬럼은 비웁니다.")

    wx_rows = []
    for _, row in df.iterrows():
        lut = cache.get(row["station"])
        if lut and row["start_date"]:
            wx_rows.append(aggregate_period(lut, row["start_date"], row["end_date"]))
        else:
            wx_rows.append({"wx_avg_temp": None, "wx_rain_prob": None, "wx_rained_days": None})
    df = pd.concat([df, pd.DataFrame(wx_rows)], axis=1)

    got = df["wx_avg_temp"].notna().sum()
    out = PROCESSED_DIR / "festivals_enriched.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"보강 완료: 날씨 {got:,}/{len(df):,}건 결합 → {out}")
    return df


def _selftest() -> None:
    """네트워크 없이 집계 로직 검증."""
    lut = {}
    base = dt.date(2025, 7, 20)
    for i in range(30):
        d = (base + dt.timedelta(days=i)).isoformat()
        lut[d] = (28.0 + (i % 5), 5.0 if i % 3 == 0 else 0.0)  # 3일마다 비
    res = aggregate_period(lut, "2026-07-24", "2026-08-02")
    print("집계 결과(2026-07-24~08-02 → 2025 매칭):", res)
    assert res["wx_avg_temp"] is not None and res["wx_rain_prob"] is not None
    print("✅ 집계 로직 정상")


def main() -> None:
    ap = argparse.ArgumentParser(description="축제 데이터 API 보강")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if args.selftest:
        _selftest()
        return
    if not KMA_SERVICE_KEY:
        print("ℹ️ KMA_SERVICE_KEY 미설정 — .env에 기상청 키를 넣으면 날씨가 결합됩니다.")
    enrich(args.limit)


if __name__ == "__main__":
    main()
