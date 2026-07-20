"""EDA — 어떤 변수가 축제 방문객수에 영향을 주는가.

문체부 2026 실측 데이터(1,266건)로, 추출한 변수들이 예측 타깃
y = 방문객수(전년) 에 어떻게·얼마나 영향을 주는지 파악한다.
데이터를 더 수집하기 전에 '무엇이 중요한 변수인지'를 먼저 안다.

분석 3단계:
  ① 수치형 변수 ↔ 방문객 상관 (Spearman, 왜곡에 강함)
  ② 범주형 변수별 방문객 중앙값 (어떤 그룹이 사람이 몰리나)
  ③ 다변량 피처 중요도 (RandomForest) + 교차검증 설명력(R²)

주의: 상관/중요도는 인과가 아니다. 특히 예산↔방문객은 양방향
(큰 축제라 예산이 크고, 예산이 커서 방문이 큰 것도 있음) — 해석 시 명시.

사용:
    python -m src.eda
"""
from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd

from src.load_festivals import load_festivals

NUMERIC = ["budget_mil_won", "budget_gov", "budget_private",
           "duration_days", "num_editions", "month"]
BOOL = ["is_annual", "gov_supported", "measured"]
CATEG = ["region", "category", "venue_type", "operator_type", "cycle"]


def _data() -> pd.DataFrame:
    df = pd.DataFrame([asdict(r) for r in load_festivals()])
    df = df[df["visitors_total"].notna() & (df["visitors_total"] > 0)].copy()
    df["log_visitors"] = np.log10(df["visitors_total"])
    return df


def numeric_impact(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("① 수치형 변수 ↔ 방문객(log) 상관 (Spearman)")
    print("=" * 60)
    rows = []
    for col in NUMERIC + BOOL:
        s = df[[col, "log_visitors"]].copy()
        s[col] = pd.to_numeric(s[col], errors="coerce")
        s = s.dropna()
        if len(s) < 30:
            continue
        r = s[col].corr(s["log_visitors"], method="spearman")
        rows.append((col, r, len(s)))
    rows.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"  {'변수':16} {'상관':>7}  {'n':>6}  방향")
    for col, r, n in rows:
        arrow = "▲ 많아짐" if r > 0 else "▼ 적어짐"
        bar = "█" * int(abs(r) * 30)
        print(f"  {col:16} {r:>7.2f}  {n:>6}  {arrow}  {bar}")


def categorical_impact(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("② 범주형 변수별 방문객 중앙값 — 어떤 그룹에 사람이 몰리나")
    print("=" * 60)
    overall = df["visitors_total"].median()
    print(f"  (전체 중앙값: {overall:,.0f}명)")
    for col in CATEG:
        g = (df.groupby(col)["visitors_total"]
             .agg(["median", "count"]).query("count >= 10")
             .sort_values("median", ascending=False))
        if g.empty:
            continue
        print(f"\n  [{col}]")
        for name, r in g.head(6).iterrows():
            ratio = r["median"] / overall
            flag = "🔥" if ratio >= 1.3 else ("·" if ratio >= 0.8 else "▽")
            print(f"    {flag} {str(name)[:16]:16} 중앙 {int(r['median']):>8,}명 "
                  f"({ratio:.1f}배)  n={int(r['count'])}")


def multivariate_importance(df: pd.DataFrame) -> None:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_score

    print("\n" + "=" * 60)
    print("③ 다변량 피처 중요도 (RandomForest, 다른 변수 통제)")
    print("=" * 60)

    X = df[NUMERIC + BOOL].apply(pd.to_numeric, errors="coerce")
    for col in NUMERIC:
        X[col] = X[col].fillna(X[col].median())
    for col in BOOL:
        X[col] = X[col].fillna(0).astype(int)
    # 범주형 원-핫 (상위 카테고리만)
    cat_dummies = pd.get_dummies(df[CATEG].astype(str), prefix=CATEG)
    keep = cat_dummies.columns[cat_dummies.sum() >= 20]     # 희소 범주 제거
    X = pd.concat([X, cat_dummies[keep]], axis=1)
    y = df["log_visitors"].values

    model = RandomForestRegressor(n_estimators=300, max_depth=8,
                                  min_samples_leaf=5, random_state=0, n_jobs=-1)
    r2 = cross_val_score(model, X, y, cv=5, scoring="r2").mean()
    model.fit(X, y)

    imp = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    print(f"  교차검증 설명력 R² = {r2:.2f}  "
          f"(방문객 변동의 {r2*100:.0f}%를 변수들로 설명)")
    print("\n  [피처 중요도 TOP 15]")
    for name, v in imp.head(15).items():
        bar = "█" * int(v / imp.max() * 30)
        print(f"    {name:22} {v:.3f}  {bar}")


def main() -> None:
    df = _data()
    print(f"분석 대상: 방문객 실측 {len(df):,}건 (전국 축제)")
    print(f"방문객 분포: 중앙 {df['visitors_total'].median():,.0f} · "
          f"최소 {df['visitors_total'].min():,.0f} · 최대 {df['visitors_total'].max():,.0f}")
    print("→ 편차가 극심(로그정규) → 이후 분석은 log 스케일 사용")
    numeric_impact(df)
    categorical_impact(df)
    multivariate_importance(df)
    print("\n⚠️ 해석 주의: 상관·중요도는 인과가 아님. "
          "예산↔방문객은 양방향(큰 축제라 예산 크고, 예산 커서 방문 큼).")


if __name__ == "__main__":
    main()
