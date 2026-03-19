from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import MaintenancePlan, User, MaintenanceFrequency, WorkOrder, WorkOrderType, WorkOrderStatus

router = APIRouter()

FREQ_DAYS = {
    MaintenanceFrequency.daily: 1,
    MaintenanceFrequency.weekly: 7,
    MaintenanceFrequency.biweekly: 14,
    MaintenanceFrequency.monthly: 30,
    MaintenanceFrequency.quarterly: 90,
    MaintenanceFrequency.semi_annual: 180,
    MaintenanceFrequency.annual: 365,
}

def calc_next_due(frequency: MaintenanceFrequency, from_date: date, custom_days: int = None) -> date:
    days = custom_days if frequency == MaintenanceFrequency.custom else FREQ_DAYS.get(frequency, 30)
    return from_date + timedelta(days=days)

@router.get("/", response_model=List[dict])
def list_plans(project_id: Optional[int]=None, asset_id: Optional[int]=None,
               db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(MaintenancePlan).filter(MaintenancePlan.is_deleted==False)
    if project_id: q = q.filter(MaintenancePlan.project_id==project_id)
    if asset_id: q = q.filter(MaintenancePlan.asset_id==asset_id)
    plans = q.all()
    return [{"id": p.id, "plan_number": p.plan_number, "name": p.name, "name_ar": p.name_ar,
             "frequency": p.frequency, "asset_id": p.asset_id, "project_id": p.project_id,
             "next_due_date": p.next_due_date, "is_active": p.is_active,
             "estimated_duration_hours": p.estimated_duration_hours} for p in plans]

@router.post("/")
def create_plan(plan_in: dict, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    from app.schemas.schemas import MaintenancePlanCreate
    count = db.query(MaintenancePlan).count()
    start = date.today()
    freq = plan_in.get("frequency", "monthly")
    next_due = calc_next_due(MaintenanceFrequency(freq), start)
    plan = MaintenancePlan(
        **{k: v for k, v in plan_in.items() if k in MaintenancePlan.__table__.columns.keys()},
        plan_number=f"PM-{count+1:05d}",
        start_date=start,
        next_due_date=next_due,
    )
    db.add(plan); db.commit(); db.refresh(plan)
    return {"id": plan.id, "plan_number": plan.plan_number, "next_due_date": plan.next_due_date}

@router.post("/{plan_id}/generate-work-order")
def generate_work_order(plan_id: int, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id==plan_id).first()
    if not plan: raise HTTPException(404, "Plan not found")
    count = db.query(WorkOrder).count()
    wo = WorkOrder(
        wo_number=f"PM-{date.today().year}-{count+1:06d}",
        title=f"Preventive Maintenance: {plan.name}",
        title_ar=f"صيانة وقائية: {plan.name_ar or plan.name}",
        wo_type=WorkOrderType.preventive,
        status=WorkOrderStatus.pending,
        project_id=plan.project_id,
        asset_id=plan.asset_id,
        maintenance_plan_id=plan.id,
        scheduled_date=plan.next_due_date,
        estimated_duration_hours=plan.estimated_duration_hours,
        estimated_cost=plan.estimated_cost,
        created_by_id=current_user.id,
        checklist_completed=plan.checklist_items,
    )
    db.add(wo)
    plan.last_executed_date = date.today()
    plan.next_due_date = calc_next_due(plan.frequency, date.today(), plan.custom_days)
    db.commit()
    return {"wo_number": wo.wo_number, "next_due_date": plan.next_due_date}
