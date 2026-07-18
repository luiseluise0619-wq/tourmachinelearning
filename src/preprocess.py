"""데이터 정합·청소 유틸.

축제 정보 + 날씨 + 방문자 데이터를 하나의 학습용 테이블로 합치기 위한
공통 전처리 함수 모음. 노트북(02_features.ipynb)에서 재사용한다.
"""
from __future__ import annotations

import pandas as pd


def parse_yyyymmdd(series: pd.Series) -> pd.Series:
    """YYYYMMDD 문자열/숫자 컬럼을 datetime 으로 변환한다."""
    return pd.to_datetime(series.astype(str).str.strip(),
                          format="%Y%m%d", errors="coerce")


def add_calendar_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """날짜에서 월·요일·주말 여부 등 달력 파생변수를 만든다."""
    out = df.copy()
    dt = pd.to_datetime(out[date_col], errors="coerce")
    out["month"] = dt.dt.month
    out["dayofweek"] = dt.dt.dayofweek          # 0=월 ... 6=일
    out["is_weekend"] = out["dayofweek"].isin([5, 6]).astype(int)
    return out


def merge_festival_weather(festivals: pd.DataFrame, weather: pd.DataFrame,
                           fest_date_col: str = "eventstartdate",
                           weather_date_col: str = "tm") -> pd.DataFrame:
    """축제-날씨를 개최일 기준으로 결합한다.

    weather 의 tm(관측일)을 datetime 으로 맞춘 뒤 축제 개최일과 조인한다.
    실제 프로젝트에서는 지역(지점번호) 매핑까지 함께 고려해야 한다.
    """
    fest = festivals.copy()
    wx = weather.copy()
    fest["_date"] = parse_yyyymmdd(fest[fest_date_col])
    wx["_date"] = pd.to_datetime(wx[weather_date_col], errors="coerce")
    return fest.merge(wx, on="_date", how="left", suffixes=("", "_wx"))


def report_missing(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼별 결측 개수·비율 요약."""
    n = len(df)
    miss = df.isna().sum()
    return (
        pd.DataFrame({"missing": miss, "ratio": (miss / n).round(3)})
        .sort_values("missing", ascending=False)
    )
