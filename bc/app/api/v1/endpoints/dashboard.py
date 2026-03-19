from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Asset, AssetStatus, WorkOrder, WorkOrderStatus, WorkOrderType,
    SparePart, Incident, NonConformance, NonConformanceStatus,
    MaintenancePlan, User, BudgetPlan, CostTransaction
)

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    def qf(model):
        q = db.query(model)
        if project_id and hasattr(model, "project_id"):
            q = q.filter(model.project_id == project_id)
        return q

    # Assets
    total_assets = qf(Asset).filter(Asset.is_deleted == False).count()
    assets_operational = qf(Asset).filter(Asset.status == AssetStatus.operational, Asset.is_deleted == False).count()
    assets_maintenance = qf(Asset).filter(Asset.status == AssetStatus.under_maintenance, Asset.is_deleted == False).count()
    assets_out = qf(Asset).filter(Asset.status == AssetStatus.out_of_service, Asset.is_deleted == False).count()
    asset_availability = round((assets_operational / total_assets * 100) if total_assets > 0 else 0, 1)

    # Work Orders
    active_statuses = [WorkOrderStatus.pending, WorkOrderStatus.assigned, WorkOrderStatus.in_progress]
    total_wo = qf(WorkOrder).filter(WorkOrder.is_deleted == False).count()
    wo_pending = qf(WorkOrder).filter(WorkOrder.status == WorkOrderStatus.pending).count()
    wo_in_progress = qf(WorkOrder).filter(WorkOrder.status == WorkOrderStatus.in_progress).count()
    wo_completed_month = qf(WorkOrder).filter(
        WorkOrder.status == WorkOrderStatus.completed,
        WorkOrder.actual_end_time >= month_start
    ).count()
    wo_overdue = qf(WorkOrder).filter(
        WorkOrder.scheduled_date < today,
        WorkOrder.status.in_(active_statuses)
    ).count()
    wo_completed_total = qf(WorkOrder).filter(WorkOrder.status == WorkOrderStatus.completed).count()
    wo_completion_rate = round((wo_completed_total / total_wo * 100) if total_wo > 0 else 0, 1)

    # MTTR (Mean Time To Repair) - avg actual duration of corrective work orders
    mttr_result = db.query(func.avg(WorkOrder.actual_duration_hours)).filter(
        WorkOrder.wo_type == WorkOrderType.corrective,
        WorkOrder.status == WorkOrderStatus.completed,
        WorkOrder.actual_duration_hours.isnot(None),
    ).scalar()
    mttr = round(float(mttr_result) if mttr_result else 0, 1)

    # Inventory
    total_parts = db.query(SparePart).filter(SparePart.is_deleted == False).count()
    low_stock = db.query(SparePart).filter(
        SparePart.quantity_in_stock <= SparePart.reorder_point,
        SparePart.is_deleted == False
    ).count()

    # HSE
    incidents_ytd = qf(Incident).filter(
        Incident.created_at >= year_start
    ).count()

    # Quality
    open_ncrs = qf(NonConformance).filter(
        NonConformance.status != NonConformanceStatus.closed
    ).count()

    # Budget
    budget_plan = None
    actual_cost = 0
    budget_used_pct = 0
    if project_id:
        budget_plan = db.query(BudgetPlan).filter(
            BudgetPlan.project_id == project_id,
            BudgetPlan.year == today.year,
        ).first()
        actual_cost_result = db.query(func.sum(CostTransaction.amount)).filter(
            CostTransaction.project_id == project_id,
            CostTransaction.transaction_date >= year_start,
        ).scalar()
        actual_cost = float(actual_cost_result or 0)
        if budget_plan and budget_plan.total_budget > 0:
            budget_used_pct = round(actual_cost / budget_plan.total_budget * 100, 1)

    # Upcoming maintenance (next 30 days)
    upcoming = db.query(MaintenancePlan).filter(
        MaintenancePlan.is_active == True,
        MaintenancePlan.next_due_date >= today,
        MaintenancePlan.next_due_date <= today + timedelta(days=30),
    )
    if project_id:
        upcoming = upcoming.filter(MaintenancePlan.project_id == project_id)
    upcoming = upcoming.order_by(MaintenancePlan.next_due_date.asc()).limit(10).all()

    # Recent work orders
    recent_wo = qf(WorkOrder).filter(WorkOrder.is_deleted == False).order_by(
        WorkOrder.created_at.desc()
    ).limit(5).all()

    return {
        "assets": {
            "total": total_assets,
            "operational": assets_operational,
            "under_maintenance": assets_maintenance,
            "out_of_service": assets_out,
            "availability_pct": asset_availability,
        },
        "work_orders": {
            "total": total_wo,
            "pending": wo_pending,
            "in_progress": wo_in_progress,
            "completed_this_month": wo_completed_month,
            "overdue": wo_overdue,
            "completion_rate": wo_completion_rate,
        },
        "kpis": {
            "mttr_hours": mttr,
            "mtbf_hours": 0,  # Requires failure log data
            "oee_pct": round(asset_availability * wo_completion_rate / 100, 1),
        },
        "inventory": {
            "total_parts": total_parts,
            "low_stock_items": low_stock,
        },
        "hse": {
            "incidents_ytd": incidents_ytd,
        },
        "quality": {
            "open_ncrs": open_ncrs,
        },
        "budget": {
            "total_budget": budget_plan.total_budget if budget_plan else 0,
            "actual_cost": actual_cost,
            "budget_used_pct": budget_used_pct,
        },
        "upcoming_maintenance": [
            {
                "id": mp.id,
                "name": mp.name,
                "name_ar": mp.name_ar,
                "asset_id": mp.asset_id,
                "frequency": mp.frequency,
                "next_due_date": mp.next_due_date.isoformat() if mp.next_due_date else None,
                "days_until_due": (mp.next_due_date - today).days if mp.next_due_date else None,
            }
            for mp in upcoming
        ],
        "recent_work_orders": [
            {
                "id": wo.id,
                "wo_number": wo.wo_number,
                "title": wo.title,
                "status": wo.status,
                "priority": wo.priority,
                "scheduled_date": wo.scheduled_date.isoformat() if wo.scheduled_date else None,
            }
            for wo in recent_wo
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/charts/work-orders-trend")
def get_wo_trend(
    project_id: Optional[int] = None,
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Work order trend for the last N months"""
    today = date.today()
    data = []
    for i in range(months - 1, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=30 * i)
        month_end = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        q = db.query(WorkOrder).filter(
            WorkOrder.created_at >= month_date,
            WorkOrder.created_at <= month_end,
            WorkOrder.is_deleted == False,
        )
        if project_id:
            q = q.filter(WorkOrder.project_id == project_id)
        data.append({
            "month": month_date.strftime("%Y-%m"),
            "month_label": month_date.strftime("%b %Y"),
            "created": q.count(),
            "completed": q.filter(WorkOrder.status == WorkOrderStatus.completed).count(),
            "preventive": q.filter(WorkOrder.wo_type == WorkOrderType.preventive).count(),
            "corrective": q.filter(WorkOrder.wo_type == WorkOrderType.corrective).count(),
        })
    return data


@router.get("/charts/asset-status")
def get_asset_status_chart(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Asset).filter(Asset.is_deleted == False)
    if project_id:
        q = q.filter(Asset.project_id == project_id)

    statuses = {}
    for status in AssetStatus:
        count = q.filter(Asset.status == status).count()
        statuses[status.value] = count

    return {"status_distribution": statuses}


@router.get("/charts/cost-trend")
def get_cost_trend(
    project_id: Optional[int] = None,
    months: int = Query(6, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    data = []
    for i in range(months - 1, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=30 * i)
        month_end = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        q = db.query(func.sum(CostTransaction.amount)).filter(
            CostTransaction.transaction_date >= month_date,
            CostTransaction.transaction_date <= month_end,
        )
        if project_id:
            q = q.filter(CostTransaction.project_id == project_id)
        actual = float(q.scalar() or 0)
        data.append({
            "month": month_date.strftime("%Y-%m"),
            "month_label": month_date.strftime("%b %Y"),
            "actual_cost": actual,
        })
    return data
