from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import WorkOrder, Asset, WorkOrderStatus, WorkOrderType, User

router = APIRouter()

@router.get("/maintenance-summary")
def maintenance_summary(project_id: Optional[int]=None, from_date: Optional[date]=None,
                        to_date: Optional[date]=None, db: Session=Depends(get_db),
                        current_user: User=Depends(get_current_user)):
    if not from_date: from_date = date.today().replace(day=1)
    if not to_date: to_date = date.today()
    q = db.query(WorkOrder).filter(WorkOrder.is_deleted==False,
                                   WorkOrder.scheduled_date>=from_date,
                                   WorkOrder.scheduled_date<=to_date)
    if project_id: q = q.filter(WorkOrder.project_id==project_id)
    total = q.count()
    completed = q.filter(WorkOrder.status==WorkOrderStatus.completed).count()
    preventive = q.filter(WorkOrder.wo_type==WorkOrderType.preventive).count()
    corrective = q.filter(WorkOrder.wo_type==WorkOrderType.corrective).count()
    avg_cost = db.query(func.avg(WorkOrder.actual_cost)).filter(
        WorkOrder.status==WorkOrderStatus.completed, WorkOrder.actual_cost>0).scalar() or 0
    return {"period": {"from": from_date, "to": to_date}, "total_work_orders": total,
            "completed": completed, "completion_rate": round(completed/total*100 if total>0 else 0,1),
            "by_type": {"preventive": preventive, "corrective": corrective},
            "avg_actual_cost": round(float(avg_cost), 2)}

@router.get("/kpi")
def kpi_report(project_id: Optional[int]=None, db: Session=Depends(get_db),
               current_user: User=Depends(get_current_user)):
    q = db.query(WorkOrder).filter(WorkOrder.is_deleted==False)
    if project_id: q = q.filter(WorkOrder.project_id==project_id)
    total = q.count()
    completed = q.filter(WorkOrder.status==WorkOrderStatus.completed).count()
    overdue = q.filter(WorkOrder.scheduled_date<date.today(),
                       WorkOrder.status.notin_([WorkOrderStatus.completed,
                                                WorkOrderStatus.cancelled])).count()
    mttr = db.query(func.avg(WorkOrder.actual_duration_hours)).filter(
        WorkOrder.wo_type==WorkOrderType.corrective,
        WorkOrder.actual_duration_hours.isnot(None)).scalar() or 0
    asset_q = db.query(Asset).filter(Asset.is_deleted==False)
    if project_id: asset_q = asset_q.filter(Asset.project_id==project_id)
    total_assets = asset_q.count()
    from app.models.models import AssetStatus
    operational = asset_q.filter(Asset.status==AssetStatus.operational).count()
    availability = round(operational/total_assets*100 if total_assets>0 else 0, 1)
    return {
        "wo_completion_rate": round(completed/total*100 if total>0 else 0, 1),
        "overdue_rate": round(overdue/total*100 if total>0 else 0, 1),
        "mttr_hours": round(float(mttr), 1),
        "asset_availability_pct": availability,
        "oee_estimate": round(availability * (completed/total*100 if total>0 else 0) / 100, 1),
    }
