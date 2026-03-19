from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Incident, PermitToWork, User

router = APIRouter()

@router.get("/incidents")
def list_incidents(project_id: Optional[int]=None, is_closed: Optional[bool]=None,
                   db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(Incident).filter(Incident.is_deleted==False)
    if project_id: q = q.filter(Incident.project_id==project_id)
    if is_closed is not None: q = q.filter(Incident.is_closed==is_closed)
    incidents = q.order_by(Incident.created_at.desc()).all()
    return [{"id": i.id, "incident_number": i.incident_number, "title": i.title,
             "severity": i.severity, "incident_date": i.incident_date,
             "location": i.location, "is_closed": i.is_closed,
             "lost_time_hours": i.lost_time_hours} for i in incidents]

@router.post("/incidents")
def create_incident(incident_in: dict, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    count = db.query(Incident).count()
    incident = Incident(**{k: v for k, v in incident_in.items() if hasattr(Incident, k)},
                        incident_number=f"INC-{date.today().year}-{count+1:04d}",
                        reported_by_id=current_user.id)
    db.add(incident); db.commit(); db.refresh(incident)
    return {"id": incident.id, "incident_number": incident.incident_number}

@router.get("/permits")
def list_permits(project_id: Optional[int]=None, db: Session=Depends(get_db),
                 current_user: User=Depends(get_current_user)):
    q = db.query(PermitToWork).filter(PermitToWork.is_deleted==False)
    if project_id: q = q.filter(PermitToWork.project_id==project_id)
    permits = q.all()
    return [{"id": p.id, "ptw_number": p.ptw_number, "permit_type": p.permit_type,
             "location": p.location, "valid_from": p.valid_from, "valid_to": p.valid_to,
             "is_approved": p.is_approved, "is_closed": p.is_closed} for p in permits]

@router.post("/permits")
def create_permit(permit_in: dict, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    count = db.query(PermitToWork).count()
    permit = PermitToWork(**{k: v for k, v in permit_in.items() if hasattr(PermitToWork, k)},
                          ptw_number=f"PTW-{date.today().year}-{count+1:04d}",
                          requestor_id=current_user.id)
    db.add(permit); db.commit(); db.refresh(permit)
    return {"id": permit.id, "ptw_number": permit.ptw_number}

@router.get("/stats")
def hse_stats(project_id: Optional[int]=None, db: Session=Depends(get_db),
              current_user: User=Depends(get_current_user)):
    q = db.query(Incident).filter(Incident.is_deleted==False)
    if project_id: q = q.filter(Incident.project_id==project_id)
    from sqlalchemy import func
    total = q.count()
    open_incidents = q.filter(Incident.is_closed==False).count()
    lti = q.filter(Incident.lost_time_hours>0).count()
    total_lth = db.query(func.sum(Incident.lost_time_hours)).scalar() or 0
    return {"total_incidents": total, "open_incidents": open_incidents,
            "lost_time_incidents": lti, "total_lost_time_hours": float(total_lth)}
