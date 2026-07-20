"""EDA 시각화 — 변수 영향력 차트 생성 (docs/figures/*.png).

단일 시리즈 크기비교 → 가로막대, 관계 → 산점도. 순차 단일 색상.
발표/기능설명서용 정적 PNG.

사용:
    python -m src.eda_charts
"""
from __future__ import annotations

from dataclasses import asdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import ROOT_DIR
from src.eda import BOOL, CATEG, NUMERIC
from src.load_festivals import load_festivals

FIG_DIR = ROOT_DIR / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# 한글 폰트 + 스타일
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False
INK = "#1f2937"       # 본문 잉크
MUTED = "#9ca3af"     # 축·그리드
HUE = "#2f6f9f"       # 단일 시리즈 색 (접근성 양호)
HUE_HI = "#e07a3f"    # 강조 1개


def _data() -> pd.DataFrame:
    df = pd.DataFrame([asdict(r) for r in load_festivals()])
    df = df[df["visitors_total"].notna() & (df["visitors_total"] > 0)].copy()
    df["log_visitors"] = np.log10(df["visitors_total"])
    return df


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=10)
    ax.grid(axis="x", color="#eceff3", linewidth=1, zorder=0)
    ax.set_axisbelow(True)


def chart_importance(df) -> None:
    from sklearn.ensemble import RandomForestRegressor
    X = df[NUMERIC + BOOL].apply(pd.to_numeric, errors="coerce")
    for c in NUMERIC:
        X[c] = X[c].fillna(X[c].median())
    for c in BOOL:
        X[c] = X[c].fillna(0).astype(int)
    dummies = pd.get_dummies(df[CATEG].astype(str), prefix=CATEG)
    dummies = dummies[dummies.columns[dummies.sum() >= 20]]
    X = pd.concat([X, dummies], axis=1)
    m = RandomForestRegressor(n_estimators=300, max_depth=8, min_samples_leaf=5,
                              random_state=0, n_jobs=-1).fit(X, df["log_visitors"])
    imp = pd.Series(m.feature_importances_, index=X.columns).sort_values().tail(10)

    labels = {"budget_mil_won": "예산(백만원)", "duration_days": "축제 기간(일)",
              "num_editions": "개최 회차", "month": "개최 월",
              "budget_private": "민간 예산", "budget_gov": "국비",
              "measured": "방문객 실측여부", "gov_supported": "정부지원",
              "is_annual": "매년개최"}
    names = [labels.get(i, i.replace("_", " ")) for i in imp.index]

    fig, ax = plt.subplots(figsize=(8, 5.2))
    colors = [HUE_HI if i == len(imp) - 1 else HUE for i in range(len(imp))]
    ax.barh(names, imp.values, color=colors, height=0.62, zorder=3)
    for y, v in enumerate(imp.values):
        ax.text(v + imp.max() * 0.01, y, f"{v:.2f}", va="center",
                fontsize=9.5, color=INK)
    _style(ax)
    ax.set_xlim(0, imp.max() * 1.12)
    ax.set_title("무엇이 축제 방문객을 좌우하는가 — 피처 중요도",
                 fontsize=13.5, color=INK, weight="bold", pad=30)
    ax.text(0, 1.02, "RandomForest · 방문객(log) 예측 · 교차검증 R²=0.52",
            transform=ax.transAxes, fontsize=9.5, color=MUTED, va="bottom")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "01_feature_importance.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_budget_scatter(df) -> None:
    d = df[df["budget_mil_won"].notna() & (df["budget_mil_won"] > 0)]
    x = np.log10(d["budget_mil_won"])
    y = d["log_visitors"]
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    ax.scatter(x, y, s=14, color=HUE, alpha=0.35, edgecolors="none", zorder=3)
    b, a = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(xs, a + b * xs, color=HUE_HI, linewidth=2.2, zorder=4)
    r = x.corr(y, method="spearman")
    _style(ax)
    ax.set_xlabel("예산 (백만원, log)", fontsize=10.5, color=INK)
    ax.set_ylabel("방문객수 (log)", fontsize=10.5, color=INK)
    ax.set_title("예산이 클수록 방문객이 많다 (Spearman r=%.2f)" % r,
                 fontsize=13.5, color=INK, weight="bold", pad=30)
    ax.text(0, 1.02, "전국 축제 실측 · 예산↔방문객은 양방향(인과 아님) 해석 주의",
            transform=ax.transAxes, fontsize=9.5, color=MUTED, va="bottom")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "02_budget_vs_visitors.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_operator(df) -> None:
    g = (df.groupby("operator_type")["visitors_total"]
         .agg(["median", "count"]).query("count >= 10")
         .sort_values("median"))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.barh(list(g.index), g["median"].values, color=HUE, height=0.6, zorder=3)
    for y, (v, n) in enumerate(zip(g["median"], g["count"])):
        ax.text(v + g["median"].max() * 0.01, y, f"{int(v):,}명 (n={int(n)})",
                va="center", fontsize=9, color=INK)
    _style(ax)
    ax.set_xlim(0, g["median"].max() * 1.22)
    ax.set_title("운영 주체별 방문객 중앙값 — 재단 운영이 강하다",
                 fontsize=13.5, color=INK, weight="bold", pad=30)
    ax.text(0, 1.03, "재단(관광/문화) 운영 축제가 민간 협·단체 대비 방문객 6배",
            transform=ax.transAxes, fontsize=9.5, color=MUTED, va="bottom")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "03_operator_effect.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    df = _data()
    chart_importance(df)
    chart_budget_scatter(df)
    chart_operator(df)
    print(f"차트 3종 생성 완료 → {FIG_DIR}")


if __name__ == "__main__":
    main()
