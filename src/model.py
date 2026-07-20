"""방문객 예측 모델 + 변수 근거(계수·유의성) 산출 — T1 근거의 실체.

Evidence Framework(docs/evidence_framework.md)의 T1(데이터 학습)을 실행한다.
문체부 실측 1,266건으로 y=log(방문객)를 예측하고,
  · OLS 회귀계수 + 95% 신뢰구간 + p값  → "어떤 변수가 유의미하게 영향?"
  · GBM 교차검증 R² + 피처 중요도       → 예측력·비선형 영향
을 뽑아 '데이터상 영향 큰 변수'를 근거와 함께 확정한다.

사용:
    python -m src.model
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict

import numpy as np
import pandas as pd

from src.config import ROOT_DIR
from src.load_festivals import load_festivals

# T1 후보 (문체부 실측 보유)
NUM_LOG = ["budget_mil_won"]              # 로그 변환 대상
NUM = ["duration_days", "num_editions", "month"]
BIN = ["is_weekend", "gov_supported", "measured"]
CAT = ["region", "category", "operator_type", "venue_type", "cycle"]


def _includes_weekend(start, end) -> int:
    if not isinstance(start, str):
        return 0
    s = dt.date.fromisoformat(start)
    e = dt.date.fromisoformat(end) if isinstance(end, str) else s
    return int(any((s + dt.timedelta(days=i)).weekday() >= 5
                   for i in range((e - s).days + 1)))


def build_frame() -> pd.DataFrame:
    df = pd.DataFrame([asdict(r) for r in load_festivals()])
    df = df[df["visitors_total"].notna() & (df["visitors_total"] > 0)].copy()
    df["y"] = np.log10(df["visitors_total"])
    df["is_weekend"] = [_includes_weekend(s, e)
                        for s, e in zip(df["start_date"], df["end_date"])]
    df["log_budget"] = np.log10(pd.to_numeric(df["budget_mil_won"],
                                              errors="coerce").fillna(0) + 1)
    for c in NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[c] = df[c].fillna(df[c].median())
    for c in BIN:
        df[c] = df[c].fillna(0).astype(int)
    for c in CAT:
        df[c] = df[c].fillna("미상").astype(str)
    return df


def _design(df: pd.DataFrame):
    """OLS/GBM 공용 설계행렬 (희소 범주 제거, 다중공선성 위해 drop_first)."""
    num = df[["log_budget"] + NUM + BIN].copy()
    dummies = pd.get_dummies(df[CAT], prefix=CAT, drop_first=True)
    dummies = dummies[dummies.columns[dummies.sum() >= 20]]  # 희소 범주 제거
    X = pd.concat([num, dummies.astype(int)], axis=1)
    return X, df["y"].values


def ols_evidence(df: pd.DataFrame) -> None:
    import statsmodels.api as sm

    X, y = _design(df)
    Xc = sm.add_constant(X)
    res = sm.OLS(y, Xc).fit()

    print("=" * 66)
    print("① OLS 회귀 — 변수별 근거 (계수·95%CI·p값)")
    print("=" * 66)
    print(f"  표본 {int(res.nobs):,}건 · 설명력 R²={res.rsquared:.2f} "
          f"(조정 R²={res.rsquared_adj:.2f})")
    print(f"\n  {'변수':22} {'효과(방문%)':>12} {'p값':>8}  유의")

    ci = res.conf_int()
    rows = []
    for name in res.params.index:
        if name == "const":
            continue
        coef = res.params[name]
        p = res.pvalues[name]
        # log10(y) 계수 → 방문객 % 변화 (연속형) / 더미는 수준차
        pct = (10 ** coef - 1) * 100
        rows.append((name, pct, p))
    # 유의미(p<0.05)한 것부터, 효과 절대값 순
    rows.sort(key=lambda r: (r[2] >= 0.05, -abs(r[1])))
    label = {"log_budget": "예산(10배당)", "duration_days": "기간(+1일)",
             "num_editions": "회차(+1)", "month": "개최월(+1)",
             "is_weekend": "주말포함", "gov_supported": "정부지원",
             "measured": "방문객실측"}
    for name, pct, p in rows[:16]:
        nm = label.get(name, name.replace("_", " "))
        star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "·"
        print(f"  {nm:22} {pct:>+11.1f}% {p:>8.3f}  {star}")
    print("\n  *** p<0.001  ** p<0.01  * p<0.05  · 비유의")


def gbm_evidence(df: pd.DataFrame) -> None:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import KFold, cross_val_score

    X, y = _design(df)
    cv = KFold(n_splits=5, shuffle=True, random_state=0)
    lin = LinearRegression()
    gbm = GradientBoostingRegressor(n_estimators=400, max_depth=3,
                                    learning_rate=0.05, subsample=0.8,
                                    random_state=0)
    r2_lin = cross_val_score(lin, X, y, cv=cv, scoring="r2").mean()
    r2_gbm = cross_val_score(gbm, X, y, cv=cv, scoring="r2").mean()

    print("\n" + "=" * 66)
    print("② 예측력 (5-fold 교차검증 R²)")
    print("=" * 66)
    print(f"  선형회귀 R² = {r2_lin:.2f}")
    print(f"  GBM      R² = {r2_gbm:.2f}   ← 채택 (비선형·상호작용 포착)")

    gbm.fit(X, y)
    imp = pd.Series(gbm.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\n  [GBM 피처 중요도 TOP 10]")
    for name, v in imp.head(10).items():
        bar = "█" * int(v / imp.max() * 28)
        print(f"    {name:22} {v:.3f}  {bar}")


def main() -> None:
    df = build_frame()
    print(f"학습 데이터: 방문객 실측 {len(df):,}건 · y=log10(방문객)\n")
    ols_evidence(df)
    gbm_evidence(df)
    print("\n→ 유의미(별표) + 중요도 상위 변수 = '데이터상 영향 큰 변수' = 모델 채택 대상")


if __name__ == "__main__":
    main()
