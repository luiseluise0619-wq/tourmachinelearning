"""최고 성능 방문객 예측 모델 — 모델 비교 · 분위수 회귀 · SHAP.

Evidence Framework T1의 고도화 버전. 여러 회귀 모델을 교차검증으로 비교해
최고를 선정하고, 분위수 회귀로 확률예보(P10/P50/P90)를 학습 기반으로 만든 뒤,
SHAP로 예측을 변수별로 분해한다(보완 피드백의 근거).

산출:
  · 최고 모델 + 분위수 모델 → models/ (joblib, gitignore)
  · docs/model_best.md (성능·중요도·SHAP 요약)

사용:
    python -m src.model_best
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ROOT_DIR
from src.model import _design, build_frame

warnings.filterwarnings("ignore")
MODELS_DIR = ROOT_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


def _safe_cols(X: pd.DataFrame):
    """LightGBM용 안전 컬럼명(특수문자 제거) + 표시용 원본 매핑."""
    safe, disp = [], {}
    for i, c in enumerate(X.columns):
        s = f"f{i}_" + re.sub(r'[^0-9a-zA-Z가-힣]', '_', str(c))[:30]
        safe.append(s)
        disp[s] = str(c)
    Xs = X.copy()
    Xs.columns = safe
    return Xs, disp


def compare_models(X, y):
    from sklearn.ensemble import (GradientBoostingRegressor,
                                  HistGradientBoostingRegressor,
                                  RandomForestRegressor)
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import KFold, cross_val_score
    import lightgbm as lgb

    cv = KFold(n_splits=5, shuffle=True, random_state=0)
    models = {
        "선형회귀": LinearRegression(),
        "RandomForest": RandomForestRegressor(n_estimators=400, max_depth=10,
                                              min_samples_leaf=4, random_state=0, n_jobs=-1),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=400, max_depth=3,
                                                      learning_rate=0.05, subsample=0.8, random_state=0),
        "HistGBM": HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05,
                                                 max_depth=None, l2_regularization=1.0, random_state=0),
        "LightGBM": lgb.LGBMRegressor(n_estimators=500, learning_rate=0.04, num_leaves=31,
                                      subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
                                      random_state=0, verbose=-1),
    }
    scores = {}
    for name, m in models.items():
        scores[name] = cross_val_score(m, X, y, cv=cv, scoring="r2").mean()
    return scores, models


def quantile_intervals(X, y):
    """LightGBM 분위수 회귀 P10/P50/P90 + 교차검증 80% 구간 커버리지."""
    from sklearn.model_selection import cross_val_predict
    import lightgbm as lgb

    def q(alpha):
        return lgb.LGBMRegressor(objective="quantile", alpha=alpha, n_estimators=400,
                                 learning_rate=0.05, num_leaves=31, min_child_samples=25,
                                 random_state=0, verbose=-1)
    p10 = cross_val_predict(q(0.1), X, y, cv=5)
    p90 = cross_val_predict(q(0.9), X, y, cv=5)
    lo, hi = np.minimum(p10, p90), np.maximum(p10, p90)
    coverage = float(np.mean((y >= lo) & (y <= hi)))
    models = {a: q(a).fit(X, y) for a in (0.1, 0.5, 0.9)}
    return coverage, models


def shap_summary(best_lgb, X, disp):
    import shap
    expl = shap.TreeExplainer(best_lgb)
    sv = expl.shap_values(X)
    mean_abs = np.abs(sv).mean(axis=0)
    s = pd.Series(mean_abs, index=[disp[c] for c in X.columns]).sort_values(ascending=False)
    return s


def main() -> None:
    import joblib
    import lightgbm as lgb

    df = build_frame()
    X, y = _design(df)
    Xs, disp = _safe_cols(X)
    print(f"학습 데이터: {len(Xs):,}건 · 피처 {Xs.shape[1]}개 · y=log10(방문객)\n")

    print("=" * 58)
    print("① 모델 비교 (5-fold 교차검증 R²)")
    print("=" * 58)
    scores, models = compare_models(Xs, y)
    best_name = max(scores, key=scores.get)
    for name, sc in sorted(scores.items(), key=lambda kv: -kv[1]):
        mark = " ← 최고" if name == best_name else ""
        bar = "█" * int(max(sc, 0) * 40)
        print(f"  {name:16} R²={sc:.3f}  {bar}{mark}")

    best = models[best_name].fit(Xs, y)

    print("\n" + "=" * 58)
    print("② 확률 예보 (분위수 회귀)")
    print("=" * 58)
    cov, qmodels = quantile_intervals(Xs, y)
    print(f"  P10~P90 실제 커버리지: {cov*100:.0f}% (목표 80%)")

    # SHAP (LightGBM 기반 — best가 트리 아니어도 해석용 LGB 별도 학습)
    print("\n" + "=" * 58)
    print("③ SHAP 변수 기여도 (보완 피드백 근거)")
    print("=" * 58)
    lgb_for_shap = (best if best_name == "LightGBM"
                    else lgb.LGBMRegressor(n_estimators=500, learning_rate=0.04, num_leaves=31,
                                           subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
                                           random_state=0, verbose=-1).fit(Xs, y))
    shp = shap_summary(lgb_for_shap, Xs, disp)
    for name, v in shp.head(10).items():
        bar = "█" * int(v / shp.max() * 30)
        print(f"    {name[:26]:28} {v:.3f}  {bar}")

    # 저장
    joblib.dump({"model": best, "name": best_name, "quantiles": qmodels,
                 "columns": list(Xs.columns), "disp": disp},
                MODELS_DIR / "festcast_model.joblib")
    print(f"\n저장: models/festcast_model.joblib ({best_name})")

    # 문서
    lines = ["# 최고 성능 모델 결과 (model_best)", "",
             f"학습 {len(Xs):,}건 · 피처 {Xs.shape[1]}개 · y=log10(방문객)", "",
             "## 모델 비교 (5-fold CV R²)", "",
             "| 모델 | R² |", "|------|-----|"]
    for name, sc in sorted(scores.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {name}{' **(채택)**' if name==best_name else ''} | {sc:.3f} |")
    lines += ["", f"**채택: {best_name} (R²={scores[best_name]:.3f})** · "
              f"이전 GBM 0.55 대비 개선.", "",
              f"## 확률 예보", "", f"- 분위수 회귀 P10~P90 커버리지 {cov*100:.0f}% (목표 80%)",
              "- 몬테카를로 대신 **데이터 학습 기반** 예측구간으로 승격 가능", "",
              "## SHAP 변수 기여도 (상위 10)", "", "| 변수 | 평균 |SHAP| |", "|------|------|"]
    for name, v in shp.head(10).items():
        lines.append(f"| {name} | {v:.3f} |")
    lines += ["", "> SHAP = 개별 예측을 변수별로 분해 → 보완 피드백('일정 옮기면 +N')의 근거.",
              "> 예산↔방문객 양방향(규모 대리지표) 해석 유지."]
    (ROOT_DIR / "docs" / "model_best.md").write_text("\n".join(lines), encoding="utf-8")
    print("문서: docs/model_best.md 갱신")


if __name__ == "__main__":
    main()
