from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import NonConformance, InspectionChecklist, NonConformanceStatus, User

router = APIRouter()

@router.get("/ncr")
def list_ncrs(project_id: Optional[int]=None, status: Optional[str]=None,
              db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(NonConformance).filter(NonConformance.is_deleted==False)
    if project_id: q = q.filter(NonConformance.project_id==project_id)
    if status: q = q.filter(NonConformance.status==status)
    ncrs = q.all()
    return [{"id": n.id, "ncr_number": n.ncr_number, "title": n.title, "severity": n.severity,
             "status": n.status, "detection_date": n.detection_date,
             "target_close_date": n.target_close_date} for n in ncrs]

@router.post("/ncr")
def create_ncr(ncr_in: dict, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    count = db.query(NonConformance).count()
    ncr = NonConformance(**{k: v for k, v in ncr_in.items() if hasattr(NonConformance, k)},
                         ncr_number=f"NCR-{date.today().year}-{count+1:04d}",
                         detected_by_id=current_user.id)
    db.add(ncr); db.commit(); db.refresh(ncr)
    return {"id": ncr.id, "ncr_number": ncr.ncr_number}

@router.get("/inspections")
def list_inspections(project_id: Optional[int]=None, db: Session=Depends(get_db),
                     current_user: User=Depends(get_current_user)):
    q = db.query(InspectionChecklist).filter(InspectionChecklist.is_deleted==False)
    if project_id: q = q.filter(InspectionChecklist.project_id==project_id)
    inspections = q.all()
    return [{"id": i.id, "checklist_number": i.checklist_number, "name": i.name,
             "inspection_date": i.inspection_date, "overall_result": i.overall_result} for i in inspections]

@router.get("/stats")
def quality_stats(project_id: Optional[int]=None, db: Session=Depends(get_db),
                  current_user: User=Depends(get_current_user)):
    q = db.query(NonConformance).filter(NonConformance.is_deleted==False)
    if project_id: q = q.filter(NonConformance.project_id==project_id)
    total = q.count()
    open_count = q.filter(NonConformance.status!=NonConformanceStatus.closed).count()
    closed = q.filter(NonConformance.status==NonConformanceStatus.closed).count()
    return {"total_ncrs": total, "open_ncrs": open_count, "closed_ncrs": closed,
            "closure_rate": round(closed/total*100 if total>0 else 0, 1)}
