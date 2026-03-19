"""
OMMS AI & Predictive Analytics Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Asset, WorkOrder, WorkOrderType, WorkOrderStatus, User
from app.services.ai_service import ai_engine

router = APIRouter()


@router.get("/fleet-health")
def get_fleet_health(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Overall fleet health analysis"""
    result = ai_engine.analyze_fleet_health(db)
    return result


@router.get("/asset-risk/{asset_id}")
def get_asset_risk(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predict failure probability for a specific asset"""
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_deleted == False).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Gather data for prediction
    today = date.today()

    # Days since last maintenance
    days_since_maint = 0
    if asset.last_maintenance_date:
        days_since_maint = (today - asset.last_maintenance_date).days

    # Recent corrective work orders (last 90 days)
    recent_corrective = db.query(WorkOrder).filter(
        WorkOrder.asset_id == asset_id,
        WorkOrder.wo_type == WorkOrderType.corrective,
        WorkOrder.created_at >= today - timedelta(days=90),
    ).count()

    # Recent incidents
    from app.models.models import Incident
    recent_incidents = db.query(Incident).filter(
        Incident.project_id == asset.project_id,
        Incident.created_at >= today - timedelta(days=90),
    ).count()

    # Expected life hours (rough calculation: 20 years * 8760 hrs)
    expected_life_hours = (asset.expected_life_years or 20) * 8760

    # Maintenance frequency from plans
    from app.models.models import MaintenancePlan, MaintenanceFrequency
    plan = db.query(MaintenancePlan).filter(
        MaintenancePlan.asset_id == asset_id,
        MaintenancePlan.is_active == True,
    ).first()

    freq_days = 30  # default monthly
    if plan:
        freq_map = {
            MaintenanceFrequency.daily: 1,
            MaintenanceFrequency.weekly: 7,
            MaintenanceFrequency.biweekly: 14,
            MaintenanceFrequency.monthly: 30,
            MaintenanceFrequency.quarterly: 90,
            MaintenanceFrequency.semi_annual: 180,
            MaintenanceFrequency.annual: 365,
        }
        freq_days = freq_map.get(plan.frequency, 30)

    result = ai_engine.predict_failure_probability(
        asset_id=asset_id,
        running_hours=asset.running_hours or 0,
        expected_life_hours=expected_life_hours,
        days_since_last_maintenance=days_since_maint,
        maintenance_frequency_days=freq_days,
        recent_corrective_wos=recent_corrective,
        recent_incidents=recent_incidents,
    )

    result["asset_name"] = asset.name
    result["asset_name_ar"] = asset.name_ar
    result["asset_code"] = asset.asset_code
    result["criticality"] = asset.criticality
    result["current_status"] = asset.status

    return result


@router.get("/high-risk-assets")
def get_high_risk_assets(
    project_id: Optional[int] = None,
    min_score: float = Query(50.0, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all assets with high failure probability"""
    query = db.query(Asset).filter(Asset.is_deleted == False)
    if project_id:
        query = query.filter(Asset.project_id == project_id)
    assets = query.all()

    today = date.today()
    high_risk = []

    for asset in assets:
        days_since_maint = 0
        if asset.last_maintenance_date:
            days_since_maint = (today - asset.last_maintenance_date).days

        recent_corrective = db.query(WorkOrder).filter(
            WorkOrder.asset_id == asset.id,
            WorkOrder.wo_type == WorkOrderType.corrective,
            WorkOrder.created_at >= today - timedelta(days=90),
        ).count()

        expected_life_hours = (asset.expected_life_years or 20) * 8760

        result = ai_engine.predict_failure_probability(
            asset_id=asset.id,
            running_hours=asset.running_hours or 0,
            expected_life_hours=expected_life_hours,
            days_since_last_maintenance=days_since_maint,
            maintenance_frequency_days=30,
            recent_corrective_wos=recent_corrective,
            recent_incidents=0,
        )

        if result["failure_probability"] >= min_score:
            result["asset_name"] = asset.name
            result["asset_name_ar"] = asset.name_ar
            result["asset_code"] = asset.asset_code
            result["criticality"] = asset.criticality
            high_risk.append(result)

    return sorted(high_risk, key=lambda x: x["failure_probability"], reverse=True)


@router.get("/maintenance-optimization/{plan_id}")
def optimize_maintenance_interval(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest optimal maintenance interval for a plan"""
    from app.models.models import MaintenancePlan, WorkOrder, WorkOrderStatus
    from sqlalchemy import func

    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    freq_map = {
        "daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30,
        "quarterly": 90, "semi_annual": 180, "annual": 365,
    }
    current_days = plan.custom_days or freq_map.get(plan.frequency.value, 30)

    # WO completion rate for this plan
    total_wos = db.query(WorkOrder).filter(WorkOrder.maintenance_plan_id == plan_id).count()
    completed = db.query(WorkOrder).filter(
        WorkOrder.maintenance_plan_id == plan_id,
        WorkOrder.status == WorkOrderStatus.completed,
    ).count()
    completion_rate = completed / total_wos if total_wos > 0 else 1.0

    result = ai_engine.predict_optimal_maintenance_interval(
        current_interval_days=current_days,
        wo_completion_rate=completion_rate,
        avg_defects_per_inspection=0.5,
        asset_criticality="critical",
    )

    result["plan_id"] = plan_id
    result["plan_name"] = plan.name
    result["total_wos_analyzed"] = total_wos
    result["completion_rate"] = round(completion_rate * 100, 1)

    return result


@router.get("/spare-parts-forecast")
def spare_parts_forecast(
    project_id: int,
    months_ahead: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast spare parts consumption for upcoming maintenance"""
    forecast = ai_engine.generate_spare_parts_forecast(db, project_id, months_ahead)
    return {
        "project_id": project_id,
        "months_ahead": months_ahead,
        "forecast_count": len(forecast),
        "items_needing_action": sum(1 for f in forecast if f["action_required"]),
        "forecast": forecast,
    }


@router.get("/mtbf-analysis")
def mtbf_analysis(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mean Time Between Failures analysis by asset"""
    from app.models.models import WorkOrder, WorkOrderType, Asset
    from sqlalchemy import func

    query = db.query(
        WorkOrder.asset_id,
        func.count(WorkOrder.id).label("failure_count"),
        func.avg(WorkOrder.actual_duration_hours).label("avg_repair_time"),
    ).filter(
        WorkOrder.wo_type == WorkOrderType.corrective,
        WorkOrder.status == WorkOrderStatus.completed,
    ).group_by(WorkOrder.asset_id)

    if project_id:
        query = query.filter(WorkOrder.project_id == project_id)

    results = query.all()
    analysis = []

    for row in results:
        asset = db.query(Asset).filter(Asset.id == row.asset_id).first()
        if not asset:
            continue

        # Rough MTBF: total running hours / failure count
        mtbf = asset.running_hours / max(row.failure_count, 1) if asset.running_hours else 0
        mttr = float(row.avg_repair_time or 0)

        analysis.append({
            "asset_id": row.asset_id,
            "asset_name": asset.name,
            "asset_code": asset.asset_code,
            "failure_count": row.failure_count,
            "mtbf_hours": round(mtbf, 1),
            "mttr_hours": round(mttr, 1),
            "availability": round(mtbf / (mtbf + mttr) * 100, 1) if (mtbf + mttr) > 0 else 100,
        })

    return sorted(analysis, key=lambda x: x["mtbf_hours"])
