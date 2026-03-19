"""
OMMS Workforce Management Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, WorkOrder, WorkOrderStatus, UserRole

router = APIRouter()


@router.get("/technicians")
def list_technicians(
    project_id: Optional[int] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all field technicians and engineers"""
    field_roles = [
        UserRole.field_technician,
        UserRole.maintenance_engineer,
        UserRole.qa_inspector,
    ]
    query = db.query(User).filter(
        User.role.in_(field_roles),
        User.is_active == is_active,
        User.is_deleted == False,
    )
    if project_id:
        query = query.filter(User.project_id == project_id)

    technicians = query.all()

    result = []
    for tech in technicians:
        # Count active WOs
        active_wos = db.query(WorkOrder).filter(
            WorkOrder.assigned_to_id == tech.id,
            WorkOrder.status.in_([WorkOrderStatus.assigned, WorkOrderStatus.in_progress]),
        ).count()

        completed_wos = db.query(WorkOrder).filter(
            WorkOrder.assigned_to_id == tech.id,
            WorkOrder.status == WorkOrderStatus.completed,
        ).count()

        result.append({
            "id": tech.id,
            "employee_id": tech.employee_id,
            "full_name": tech.full_name,
            "full_name_ar": tech.full_name_ar,
            "role": tech.role,
            "department": tech.department,
            "job_title": tech.job_title,
            "phone": tech.phone,
            "is_active": tech.is_active,
            "active_work_orders": active_wos,
            "completed_work_orders": completed_wos,
            "workload": "heavy" if active_wos >= 5 else "moderate" if active_wos >= 2 else "light",
        })

    return result


@router.get("/workload")
def get_workload_summary(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get workload distribution across all technicians"""
    query = db.query(
        WorkOrder.assigned_to_id,
        func.count(WorkOrder.id).label("total"),
        func.sum(
            func.case(
                (WorkOrder.status == WorkOrderStatus.in_progress, 1), else_=0
            )
        ).label("in_progress"),
        func.sum(
            func.case(
                (WorkOrder.status == WorkOrderStatus.completed, 1), else_=0
            )
        ).label("completed"),
    ).filter(
        WorkOrder.assigned_to_id.isnot(None),
        WorkOrder.is_deleted == False,
    ).group_by(WorkOrder.assigned_to_id)

    if project_id:
        query = query.filter(WorkOrder.project_id == project_id)

    rows = query.all()
    result = []

    for row in rows:
        user = db.query(User).filter(User.id == row.assigned_to_id).first()
        if user:
            result.append({
                "technician_id": row.assigned_to_id,
                "name": user.full_name,
                "name_ar": user.full_name_ar,
                "total_assigned": row.total,
                "in_progress": row.in_progress or 0,
                "completed": row.completed or 0,
            })

    return result


@router.get("/performance/{user_id}")
def get_technician_performance(
    user_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get performance metrics for a specific technician"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(WorkOrder).filter(WorkOrder.assigned_to_id == user_id)
    if from_date:
        query = query.filter(WorkOrder.scheduled_date >= from_date)
    if to_date:
        query = query.filter(WorkOrder.scheduled_date <= to_date)

    total = query.count()
    completed = query.filter(WorkOrder.status == WorkOrderStatus.completed).count()
    overdue = query.filter(WorkOrder.is_overdue == True).count()

    avg_duration = db.query(func.avg(WorkOrder.actual_duration_hours)).filter(
        WorkOrder.assigned_to_id == user_id,
        WorkOrder.status == WorkOrderStatus.completed,
        WorkOrder.actual_duration_hours.isnot(None),
    ).scalar() or 0

    return {
        "technician": {
            "id": user.id,
            "name": user.full_name,
            "role": user.role,
            "department": user.department,
        },
        "metrics": {
            "total_assigned": total,
            "completed": completed,
            "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
            "overdue_count": overdue,
            "avg_completion_hours": round(float(avg_duration), 1),
        },
    }
