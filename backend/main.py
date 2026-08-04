from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models
import schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="FestCast API", description="AI Platform for Festival Planning")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import List
from ai_engine import ai_model
from planner import planner

@app.get("/")
def read_root():
    return {"message": "Welcome to FestCast API"}

@app.post("/api/festivals", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/api/festivals", response_model=List[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    projects = db.query(models.Project).offset(skip).limit(limit).all()
    return projects

@app.get("/api/festivals/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.post("/api/festivals/{project_id}/analyze", response_model=schemas.AnalysisResult)
def analyze_project(project_id: int, db: Session = Depends(get_db)):
    # 1. Fetch Project
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # If analysis already exists, return it
    existing_analysis = db.query(models.AnalysisResult).filter(models.AnalysisResult.project_id == project_id).first()
    if existing_analysis:
        return existing_analysis

    # Convert SQLAlchemy model to Pydantic schema for the engines
    project_schema = schemas.ProjectCreate.model_validate(db_project, from_attributes=True)

    # 2. Run ML Prediction
    predicted_visitors, success_prob = ai_model.predict(project_schema)
    feature_importance_json = ai_model.get_feature_importance()

    # 3. Run LLM Planner
    generated_plan_json = planner.generate_plan(project_schema, predicted_visitors, success_prob)

    # 4. Save Results
    db_analysis = models.AnalysisResult(
        project_id=project_id,
        predicted_visitors=predicted_visitors,
        success_probability=success_prob,
        feature_importance=feature_importance_json,
        generated_plan=generated_plan_json
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    return db_analysis
