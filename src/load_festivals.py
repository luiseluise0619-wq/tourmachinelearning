"""문화체육관광부 '2026년 지역축제 개최계획' 엑셀 로더.

전국 1,266개 축제의 실측 데이터를 FestCast 학습·검증용으로 정규화한다.
특히 이 시드는 아래 **실측치**를 담고 있어 예측 타깃/검증 자료로 매우 귀중하다:
  · 방문객수(전년)  → 예측 타깃 y
  · 내국인/외국인 분리 방문객 → 외국인 예측·K콘텐츠 논지 검증
  · 예산 · 총일수 · 최초개최연도(→회차) · 축제 유형 · 지역

사용:
    python -m src.load_festivals                 # 요약 출력 + processed CSV 저장
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass

from src.config import PROCESSED_DIR, ROOT_DIR

SEED_PATH = ROOT_DIR / "data" / "seed" / "2026_festivals.xlsx"

# 엑셀 컬럼 인덱스 (0-based). 데이터는 9행부터.
C_SEQ, C_REGION, C_SIGUNGU_TOP, C_TITLE, C_CATEGORY, C_PLACE, C_TYPE2 = 1, 2, 3, 4, 5, 6, 7
C_SIGUNGU = 9
C_SY, C_SM, C_SD = 11, 12, 13
C_EY, C_EM, C_ED = 14, 15, 16
C_DURATION, C_CYCLE, C_FIRST_YEAR = 17, 19, 20
C_BUDGET_MIL = 21           # 예산 합계(백만원)
C_BUDGET_GOV, C_BUDGET_LOCAL, C_BUDGET_PRIVATE = 22, 23, 24   # 국비/지방비/민간
C_GOV_MINISTRY = 25         # 국비지원 부처명 (해당없음=미지원)
C_VISITORS, C_DOMESTIC, C_FOREIGN = 26, 27, 28
C_MEASURE, C_MEASURE_NOTE = 29, 30   # 계측방법(계측/추정), 유인/무인
C_ORGANIZER, C_ORG_TYPE = 31, 32     # 전담조직명, 조직형태


@dataclass
class FestivalRecord:
    seq: str
    title: str
    region: str | None
    sigungu: str | None
    place: str | None
    category: str | None          # 축제 유형 (문화예술/자연생태 등)
    venue_type: str | None        # 유형2 (마을형/녹지형/수변형 등)
    start_date: str | None
    end_date: str | None
    month: int | None
    duration_days: int | None
    first_year: int | None
    num_editions: int | None
    cycle: str | None             # 개최주기 (매년/격년/비정기)
    is_annual: bool               # 매년 개최 여부
    budget_mil_won: float | None  # 예산 합계(백만원)
    budget_gov: float | None      # 국비(백만원)
    budget_local: float | None    # 지방비(백만원)
    budget_private: float | None  # 기타/민간(백만원)
    gov_supported: bool           # 중앙정부(부처) 지원 여부
    gov_ministry: str | None      # 지원 부처명
    visitors_total: int | None    # 방문객수(전년, 실측)
    visitors_domestic: int | None
    visitors_foreign: int | None
    foreign_ratio: float | None   # 외국인/전체
    measured: bool                # 계측(실측) 여부 (아니면 추정)
    measure_note: str | None      # 유인/무인 등
    organizer: str | None
    operator_type: str | None     # 조직형태 (정부/지자체·재단·민간위탁 등)


def _clean(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return None if s in ("", "-", "모름", "미정") else s


def _strip_code(v) -> str | None:
    """'01. 문화예술' → '문화예술'."""
    s = _clean(v)
    if not s:
        return None
    if "." in s[:5] and s.split(".", 1)[0].strip().isdigit():
        s = s.split(".", 1)[1].strip()
    return s or None


def _num(v) -> int | None:
    s = _clean(v)
    if not s:
        return None
    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return None


def _fnum(v) -> float | None:
    n = _num(v)
    return float(n) if n is not None else None


def _date(y, m, d) -> dt.date | None:
    try:
        return dt.date(int(float(y)), int(float(m)), int(float(d)))
    except (TypeError, ValueError):
        return None


def load_festivals(path=SEED_PATH) -> list[FestivalRecord]:
    """엑셀을 읽어 정규화된 축제 레코드 리스트를 반환한다."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    out: list[FestivalRecord] = []

    for row in ws.iter_rows(min_row=9, values_only=True):
        def g(i):
            return row[i] if len(row) > i else None

        title = _clean(g(C_TITLE))
        if not title:
            continue

        start = _date(g(C_SY), g(C_SM), g(C_SD))
        end = _date(g(C_EY), g(C_EM), g(C_ED)) or start
        first_year = _num(g(C_FIRST_YEAR))
        total = _num(g(C_VISITORS))
        dom = _num(g(C_DOMESTIC))
        frn = _num(g(C_FOREIGN))
        fratio = round(frn / total, 3) if (total and frn is not None and total > 0) else None

        cycle = _strip_code(g(C_CYCLE))
        ministry = _clean(g(C_GOV_MINISTRY))
        if ministry in ("해당없음", "없음"):
            ministry = None
        budget_gov = _fnum(g(C_BUDGET_GOV))
        measure = _strip_code(g(C_MEASURE))

        out.append(FestivalRecord(
            seq=str(_clean(g(C_SEQ)) or title)[:64],
            title=title,
            region=_strip_code(g(C_REGION)),
            sigungu=_clean(g(C_SIGUNGU)) or _clean(g(C_SIGUNGU_TOP)),
            place=_clean(g(C_PLACE)),
            category=_strip_code(g(C_CATEGORY)),
            venue_type=_strip_code(g(C_TYPE2)),
            start_date=start.isoformat() if start else None,
            end_date=end.isoformat() if end else None,
            month=start.month if start else None,
            duration_days=_num(g(C_DURATION)),
            first_year=first_year,
            num_editions=(2026 - first_year + 1) if first_year and first_year <= 2026 else None,
            cycle=cycle,
            is_annual=(cycle == "매년"),
            budget_mil_won=_fnum(g(C_BUDGET_MIL)),
            budget_gov=budget_gov,
            budget_local=_fnum(g(C_BUDGET_LOCAL)),
            budget_private=_fnum(g(C_BUDGET_PRIVATE)),
            gov_supported=bool(ministry) or bool(budget_gov and budget_gov > 0),
            gov_ministry=ministry,
            visitors_total=total,
            visitors_domestic=dom,
            visitors_foreign=frn,
            foreign_ratio=fratio,
            measured=(measure == "계측"),
            measure_note=_strip_code(g(C_MEASURE_NOTE)),
            organizer=_clean(g(C_ORGANIZER)),
            operator_type=_strip_code(g(C_ORG_TYPE)),
        ))
    return out


def main() -> None:
    import pandas as pd

    recs = load_festivals()
    df = pd.DataFrame([asdict(r) for r in recs])
    out_path = PROCESSED_DIR / "festivals_2026.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"로드 완료: {len(df):,}건 · {len(df.columns)}개 컬럼 → {out_path}")
    print("\n[컬럼별 실측치 보유 건수]")
    for col in ("visitors_total", "visitors_domestic", "visitors_foreign",
                "budget_mil_won", "budget_gov", "budget_private",
                "num_editions", "duration_days", "cycle", "operator_type"):
        print(f"  {col:20}: {df[col].notna().sum():,}")
    print("\n[파생 플래그 분포]")
    print(f"  매년 개최(is_annual)     : {int(df['is_annual'].sum()):,}건")
    print(f"  중앙정부 지원(gov_supported): {int(df['gov_supported'].sum()):,}건")
    print(f"  방문객 실측(measured)     : {int(df['measured'].sum()):,}건")
    print(f"\n방문객수 중앙값: {df['visitors_total'].median():,.0f}명 · "
          f"예산 중앙값: {df['budget_mil_won'].median():,.0f}백만원")


if __name__ == "__main__":
    main()
