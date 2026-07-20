"""실데이터 분석 — FestCast 핵심 논지를 실측치로 검증한다.

전국 1,266개 축제의 실측 방문객(내국인/외국인)·예산·회차로:
  · 외국인 유치 실태 (K콘텐츠·외국인 논지의 근거)
  · 방문객 ↔ 예산/회차 관계
를 뽑아 공모전 발표 자료의 '데이터 근거'로 쓴다.

사용:
    python -m src.analyze_real
"""
from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from src.load_festivals import load_festivals


def _df() -> pd.DataFrame:
    return pd.DataFrame([asdict(r) for r in load_festivals()])


def foreign_insights(df: pd.DataFrame) -> None:
    fdf = df[df["visitors_foreign"].notna() & df["visitors_total"].notna()]
    fdf = fdf[fdf["visitors_total"] >= 5000]     # 규모 너무 작은 건 제외
    print(f"\n=== 외국인 방문 실태 (실측 {len(fdf):,}건) ===")
    print(f"평균 외국인 비율: {fdf['foreign_ratio'].mean()*100:.1f}%")
    print(f"외국인 방문객 총합: {fdf['visitors_foreign'].sum():,.0f}명")

    print("\n[외국인 비율 TOP 10] — '외국인이 몰리는 축제'의 특징 = 우리 타깃 모델")
    top = fdf.sort_values("foreign_ratio", ascending=False).head(10)
    for _, r in top.iterrows():
        print(f"  {r['foreign_ratio']*100:5.1f}%  {r['title'][:28]:30} "
              f"(외국 {int(r['visitors_foreign']):,} / 전체 {int(r['visitors_total']):,})")

    print("\n[외국인 절대수 TOP 10]")
    top2 = fdf.sort_values("visitors_foreign", ascending=False).head(10)
    for _, r in top2.iterrows():
        print(f"  외국 {int(r['visitors_foreign']):>10,}명  "
              f"({r['foreign_ratio']*100:4.1f}%)  {r['title'][:30]}")

    print("\n[유형별 평균 외국인 비율]")
    by_cat = (fdf.groupby("category")["foreign_ratio"].agg(["mean", "count"])
              .query("count >= 5").sort_values("mean", ascending=False))
    for cat, r in by_cat.iterrows():
        print(f"  {r['mean']*100:5.1f}%  {cat}  (n={int(r['count'])})")


def scale_insights(df: pd.DataFrame) -> None:
    import numpy as np
    d = df[df["visitors_total"].notna() & (df["visitors_total"] > 0)].copy()
    d["log_visitors"] = np.log10(d["visitors_total"])

    print("\n=== 방문객 규모 요인 (상관계수) ===")
    b = d[d["budget_mil_won"].notna() & (d["budget_mil_won"] > 0)]
    corr_budget = np.corrcoef(np.log10(b["budget_mil_won"]), b["log_visitors"])[0, 1]
    print(f"  log(예산) ↔ log(방문객): r = {corr_budget:.2f}  "
          f"(예산 큰 축제일수록 방문 많음 → 예산은 유의미한 피처)")

    e = d[d["num_editions"].notna()]
    corr_ed = np.corrcoef(e["num_editions"], e["log_visitors"])[0, 1]
    print(f"  회차(연륜) ↔ log(방문객): r = {corr_ed:.2f}  "
          f"(오래된 축제일수록 방문 많음 → 평판 피처 근거)")

    print("\n[지역별 축제 수 · 평균 방문객] (상위 8)")
    by_region = (d.groupby("region")["visitors_total"]
                 .agg(["count", "median"]).sort_values("count", ascending=False).head(8))
    for reg, r in by_region.iterrows():
        print(f"  {reg:6} 축제 {int(r['count']):>4}개 · 중앙 방문 {int(r['median']):>8,}명")


def main() -> None:
    df = _df()
    print(f"분석 대상: 전국 {len(df):,}개 축제 (문체부 2026 실측)")
    foreign_insights(df)
    scale_insights(df)


if __name__ == "__main__":
    main()
