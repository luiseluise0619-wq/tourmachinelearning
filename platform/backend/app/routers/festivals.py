"""축제 데이터 입력 CRUD + CSV 업로드."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models import Festival, Project, User
from app.schemas import FestivalIn, FestivalOut

router = APIRouter(prefix="/api/projects/{pid}/festivals", tags=["festivals"])


def _own_project(db, user, pid) -> Project:
    p = db.query(Project).filter(Project.id == pid, Project.owner_id == user.id).first()
    if not p:
        raise HTTPException(404, "프로젝트를 찾을 수 없습니다.")
    return p


@router.get("", response_model=list[FestivalOut])
def list_festivals(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _own_project(db, user, pid)
    return db.query(Festival).filter(Festival.project_id == pid).all()


@router.post("", response_model=FestivalOut)
def add_festival(pid: int, body: FestivalIn, db: Session = Depends(get_db),
                 user: User = Depends(current_user)):
    _own_project(db, user, pid)
    f = Festival(project_id=pid, **body.model_dump())
    f.is_free = 1 if body.is_free else 0
    db.add(f); db.commit(); db.refresh(f)
    return _to_out(f)


@router.post("/upload-csv")
def upload_csv(pid: int, file: UploadFile = File(...), db: Session = Depends(get_db),
               user: User = Depends(current_user)):
    """CSV 업로드 — 헤더: name,region,start_date,end_date,duration_days,budget_mil_won,visitors_total,is_free"""
    _own_project(db, user, pid)
    text = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    n = 0
    for row in reader:
        if not row.get("name"):
            continue
        f = Festival(
            project_id=pid, name=row["name"], region=row.get("region"),
            start_date=row.get("start_date"), end_date=row.get("end_date"),
            duration_days=int(row["duration_days"]) if row.get("duration_days") else None,
            budget_mil_won=float(row["budget_mil_won"]) if row.get("budget_mil_won") else None,
            visitors_total=int(row["visitors_total"]) if row.get("visitors_total") else None,
            is_free=0 if str(row.get("is_free", "1")).lower() in ("0", "false", "n") else 1,
        )
        db.add(f); n += 1
    db.commit()
    return {"ok": True, "inserted": n}


def _to_out(f: Festival) -> FestivalOut:
    d = {c.name: getattr(f, c.name) for c in f.__table__.columns}
    d["is_free"] = bool(f.is_free)
    return FestivalOut(**{k: v for k, v in d.items() if k in FestivalOut.model_fields or k in ("id", "project_id")})
