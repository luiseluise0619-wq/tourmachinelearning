"""프로젝트 CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models import Project, User
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Project).filter(Project.owner_id == user.id).order_by(Project.id.desc()).all()


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db),
                   user: User = Depends(current_user)):
    p = Project(owner_id=user.id, name=body.name, description=body.description)
    db.add(p); db.commit(); db.refresh(p)
    return p


def _own(db, user, pid) -> Project:
    p = db.query(Project).filter(Project.id == pid, Project.owner_id == user.id).first()
    if not p:
        raise HTTPException(404, "프로젝트를 찾을 수 없습니다.")
    return p


@router.get("/{pid}", response_model=ProjectOut)
def get_project(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _own(db, user, pid)


@router.delete("/{pid}")
def delete_project(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.delete(_own(db, user, pid)); db.commit()
    return {"ok": True}
