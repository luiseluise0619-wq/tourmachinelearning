"""FestCast Platform — FastAPI 엔트리포인트.

실행: uvicorn app.main:app --reload --port 8000
문서: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.deps import current_user
from app.models import Festival, Project, User
from app.routers import analysis, auth, festivals, projects, reports
from app.services.sample_data import sample_festivals


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="FestCast Platform API",
              description="축제 기획 AI SaaS — 방문객 예측·성공진단·생성기획",
              version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False, allow_methods=["*"], allow_headers=["*"],
)

for r in (auth.router, projects.router, festivals.router, analysis.router, reports.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "festcast-platform"}


@app.post("/api/dev/seed", tags=["dev"])
def seed(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """현재 사용자에 데모 프로젝트 + 샘플 축제 생성."""
    p = Project(owner_id=user.id, name="데모 프로젝트", description="샘플 축제 데이터")
    db.add(p); db.commit(); db.refresh(p)
    n = 0
    for s in sample_festivals():
        f = Festival(project_id=p.id, **{**s, "is_free": 1 if s.get("is_free", True) else 0})
        db.add(f); n += 1
    db.commit()
    return {"ok": True, "project_id": p.id, "festivals": n}
