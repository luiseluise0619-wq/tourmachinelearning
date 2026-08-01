"""AI 분석 — 방문객 예측 · 성공 진단 · 생성형 기획 · 모델 비교."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models import Analysis, User
from app.schemas import GenerateRequest, PredictRequest
from app.services import ml
from app.services.llm import generate_plan

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _save(db, project_id, kind, inputs, result):
    if project_id:
        db.add(Analysis(project_id=project_id, kind=kind, inputs=inputs, result=result))
        db.commit()


@router.post("/predict")
def predict(body: PredictRequest, project_id: int | None = None,
            db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = body.festival.model_dump()
    result = ml.predict(f)
    _save(db, project_id, "predict", f, result)
    return result


@router.post("/success")
def success(body: PredictRequest, project_id: int | None = None,
            db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = body.festival.model_dump()
    result = ml.success_analysis(f)
    _save(db, project_id, "success", f, result)
    return result


@router.post("/generate")
def generate(body: GenerateRequest, db: Session = Depends(get_db),
             user: User = Depends(current_user)):
    req = body.model_dump()
    plan = generate_plan(req)
    # 생성된 컨셉을 예측 엔진으로 검증(예상 방문객 첨부)
    try:
        est = ml.predict({
            "name": plan.get("concept", "신규 축제"), "region": body.region.split()[0],
            "budget_mil_won": body.budget_mil_won, "duration_days": 3,
            "content": {"num_programs": len(plan.get("programs", [])) or 5,
                        "performance": True, "food": True, "experience": True},
        })
        plan["predicted_visitors"] = est["expected_visitors"]
        plan["success_probability"] = est["success_probability"]
    except Exception:
        pass
    _save(db, body.project_id, "generate", req, plan)
    return plan


@router.get("/model-comparison")
def model_comparison(user: User = Depends(current_user)):
    """XGBoost/RF/GBM 교차검증 R² 비교 + 영향변수 TOP10."""
    return ml.model_comparison()


@router.get("/history/{project_id}")
def history(project_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Analysis).filter(Analysis.project_id == project_id)\
        .order_by(Analysis.id.desc()).limit(50).all()
    return [{"id": r.id, "kind": r.kind, "created_at": r.created_at.isoformat(),
             "result": r.result} for r in rows]
