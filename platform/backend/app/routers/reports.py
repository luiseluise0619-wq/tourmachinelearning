"""보고서 생성 + PDF export."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.deps import current_user
from app.models import User
from app.schemas import PredictRequest
from app.services import ml
from app.services.pdf import report_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _sections(f: dict, p: dict) -> list[tuple[str, list[str]]]:
    v = p
    secs = [
        ("1. 축제 개요", [
            f"축제명: {f.get('name','-')}",
            f"지역/기간: {f.get('region','-')} · {f.get('start_date','-')}~{f.get('end_date','-')}",
            f"예산: {f.get('budget_mil_won','-')}백만원",
        ]),
        ("2. 흥행 예보", [
            f"흥행도: {v['appeal_score']}점 ({v['grade']})",
            f"성공 확률: {round(v['success_probability']*100)}%",
            f"예상 방문객: {v['expected_visitors']:,}명 "
            f"(내국 {v['domestic']:,} / 외국 {v['foreign']:,})",
            f"80% 예측구간: {v['interval_80'][0]:,}~{v['interval_80'][1]:,}명",
        ]),
        ("3. 흥행 요인", [f"- {t['factor']}: {t['score']}점" for t in v["top_factors"]]),
        ("4. 보완 피드백", [f"- {fb['issue']}: {fb['action']}" for fb in v["feedback"][:8]]),
        ("5. 마케팅 추천", [
            f"주 타깃: {v['marketing']['primary_segment']}",
            f"채널: {', '.join(v['marketing']['recommended_channels'])}",
            f"프로그램: {v['marketing']['program_focus']}",
        ]),
    ]
    oc = v.get("overcrowding", {})
    if oc.get("prob_pct") is not None:
        secs.insert(2, ("2-1. 쏠림 위험",
                        [f"수용 {oc.get('capacity'):,}명 초과 확률: {oc['prob_pct']}% ({oc['risk']})"]))
    return secs


@router.post("/pdf")
def report_pdf_endpoint(body: PredictRequest, user: User = Depends(current_user)):
    f = body.festival.model_dump()
    p = ml.predict(f)
    pdf = report_pdf(f"FestCast 흥행 예보 리포트 — {f.get('name','축제')}", _sections(f, p))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="festcast_report.pdf"'})
