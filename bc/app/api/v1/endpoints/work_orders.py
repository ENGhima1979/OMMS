from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from datetime import date, datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import WorkOrder, WorkOrderStatus, WorkOrderType, WorkOrderPriority, User, Asset
from app.schemas.schemas import WorkOrderCreate, WorkOrderUpdate, WorkOrderResponse

router = APIRouter()


def generate_wo_number(db: Session, wo_type: WorkOrderType) -> str:
    prefix_map = {
        WorkOrderType.preventive: "PM",
        WorkOrderType.corrective: "CM",
        WorkOrderType.predictive: "PD",
        WorkOrderType.emergency: "EM",
        WorkOrderType.inspection: "IN",
        WorkOrderType.calibration: "CA",
    }
    prefix = prefix_map.get(wo_type, "WO")
    count = db.query(WorkOrder).count()
    year = datetime.now().year
    return f"{prefix}-{year}-{count + 1:06d}"


@router.get("/", response_model=List[WorkOrderResponse])
def list_work_orders(
    project_id: Optional[int] = None,
    status: Optional[WorkOrderStatus] = None,
    wo_type: Optional[WorkOrderType] = None,
    priority: Optional[WorkOrderPriority] = None,
    asset_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    overdue_only: bool = False,
    scheduled_from: Optional[date] = None,
    scheduled_to: Optional[date] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(WorkOrder).filter(WorkOrder.is_deleted == False)

    if project_id:
        query = query.filter(WorkOrder.project_id == project_id)
    if status:
        query = query.filter(WorkOrder.status == status)
    if wo_type:
        query = query.filter(WorkOrder.wo_type == wo_type)
    if priority:
        query = query.filter(WorkOrder.priority == priority)
    if asset_id:
        query = query.filter(WorkOrder.asset_id == asset_id)
    if assigned_to_id:
        query = query.filter(WorkOrder.assigned_to_id == assigned_to_id)
    if overdue_only:
        query = query.filter(
            and_(
                WorkOrder.scheduled_date < date.today(),
                WorkOrder.status.notin_([WorkOrderStatus.completed, WorkOrderStatus.cancelled, WorkOrderStatus.verified])
            )
        )
    if scheduled_from:
        query = query.filter(WorkOrder.scheduled_date >= scheduled_from)
    if scheduled_to:
        query = query.filter(WorkOrder.scheduled_date <= scheduled_to)
    if search:
        query = query.filter(
            or_(
                WorkOrder.title.ilike(f"%{search}%"),
                WorkOrder.wo_number.ilike(f"%{search}%"),
            )
        )

    # Mark overdue
    today = date.today()
    active_statuses = [WorkOrderStatus.pending, WorkOrderStatus.assigned, WorkOrderStatus.in_progress]
    
    total = query.count()
    work_orders = query.order_by(WorkOrder.scheduled_date.asc()).offset((page - 1) * per_page).limit(per_page).all()

    for wo in work_orders:
        if wo.scheduled_date and wo.scheduled_date < today and wo.status in active_statuses:
            wo.is_overdue = True

    return work_orders


@router.post("/", response_model=WorkOrderResponse, status_code=201)
def create_work_order(
    wo_in: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wo_number = generate_wo_number(db, wo_in.wo_type)

    work_order = WorkOrder(
        **wo_in.dict(),
        wo_number=wo_number,
        created_by_id=current_user.id,
        status=WorkOrderStatus.pending,
    )
    db.add(work_order)
    db.commit()
    db.refresh(work_order)

    # Create notification for assigned user
    if wo_in.assigned_to_id:
        _create_wo_notification(db, work_order, wo_in.assigned_to_id)

    return work_order


@router.get("/{wo_id}", response_model=WorkOrderResponse)
def get_work_order(
    wo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id, WorkOrder.is_deleted == False).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return wo


@router.put("/{wo_id}", response_model=WorkOrderResponse)
def update_work_order(
    wo_id: int,
    wo_in: WorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id, WorkOrder.is_deleted == False).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    for field, value in wo_in.dict(exclude_unset=True).items():
        setattr(wo, field, value)

    # Auto-set completion time
    if wo_in.status == WorkOrderStatus.completed and not wo.actual_end_time:
        wo.actual_end_time = datetime.utcnow()

    # Auto-set start time
    if wo_in.status == WorkOrderStatus.in_progress and not wo.actual_start_time:
        wo.actual_start_time = datetime.utcnow()

    # Update asset last maintenance date on completion
    if wo_in.status == WorkOrderStatus.completed:
        asset = db.query(Asset).filter(Asset.id == wo.asset_id).first()
        if asset:
            asset.last_maintenance_date = date.today()

    db.commit()
    db.refresh(wo)
    return wo


@router.patch("/{wo_id}/assign")
def assign_work_order(
    wo_id: int,
    technician_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    technician = db.query(User).filter(User.id == technician_id, User.is_active == True).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")

    wo.assigned_to_id = technician_id
    wo.status = WorkOrderStatus.assigned
    db.commit()
    _create_wo_notification(db, wo, technician_id)
    return {"message": f"Work order assigned to {technician.full_name}"}


@router.patch("/{wo_id}/complete")
def complete_work_order(
    wo_id: int,
    completion_notes: str = "",
    actual_duration_hours: float = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    wo.status = WorkOrderStatus.completed
    wo.actual_end_time = datetime.utcnow()
    wo.completion_notes = completion_notes
    wo.actual_duration_hours = actual_duration_hours

    asset = db.query(Asset).filter(Asset.id == wo.asset_id).first()
    if asset:
        asset.last_maintenance_date = date.today()

    db.commit()
    return {"message": "Work order completed successfully"}


@router.get("/stats/summary")
def get_work_order_stats(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(WorkOrder).filter(WorkOrder.is_deleted == False)
    if project_id:
        query = query.filter(WorkOrder.project_id == project_id)

    today = date.today()
    total = query.count()
    pending = query.filter(WorkOrder.status == WorkOrderStatus.pending).count()
    in_progress = query.filter(WorkOrder.status == WorkOrderStatus.in_progress).count()
    completed = query.filter(WorkOrder.status == WorkOrderStatus.completed).count()
    overdue = query.filter(
        WorkOrder.scheduled_date < today,
        WorkOrder.status.notin_([WorkOrderStatus.completed, WorkOrderStatus.cancelled, WorkOrderStatus.verified])
    ).count()

    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "overdue": overdue,
        "completion_rate": round((completed / total * 100) if total > 0 else 0, 1),
    }


def _create_wo_notification(db: Session, wo: WorkOrder, user_id: int):
    from app.models.models import Notification
    notif = Notification(
        user_id=user_id,
        title=f"New Work Order Assigned: {wo.wo_number}",
        title_ar=f"أمر عمل جديد: {wo.wo_number}",
        message=f"You have been assigned work order {wo.wo_number}: {wo.title}",
        message_ar=f"تم تعيينك في أمر العمل {wo.wo_number}: {wo.title_ar or wo.title}",
        notification_type="wo_assigned",
        reference_type="work_order",
        reference_id=wo.id,
    )
    db.add(notif)
    db.commit()
