from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project, User
from app.schemas.schemas import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()

@router.get("/", response_model=List[ProjectResponse])
def list_projects(search: Optional[str]=None, page: int=Query(1,ge=1), per_page: int=Query(20,ge=1,le=100),
                  db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(Project).filter(Project.is_deleted==False)
    if search: q = q.filter(Project.name.ilike(f"%{search}%"))
    return q.offset((page-1)*per_page).limit(per_page).all()

@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(project_in: ProjectCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    if db.query(Project).filter(Project.code==project_in.code).first():
        raise HTTPException(400, "Project code already exists")
    project = Project(**project_in.dict())
    db.add(project); db.commit(); db.refresh(project)
    return project

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    project = db.query(Project).filter(Project.id==project_id, Project.is_deleted==False).first()
    if not project: raise HTTPException(404, "Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project_in: ProjectUpdate, db: Session=Depends(get_db),
                   current_user: User=Depends(get_current_user)):
    project = db.query(Project).filter(Project.id==project_id).first()
    if not project: raise HTTPException(404, "Project not found")
    for f, v in project_in.dict(exclude_unset=True).items():
        setattr(project, f, v)
    db.commit(); db.refresh(project)
    return project
