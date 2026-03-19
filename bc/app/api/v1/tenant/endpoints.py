"""
OMMS Tenant API — Projects, Dams, Components, Readings, Workers
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, timedelta
import json, io

router = APIRouter()

# Lazy import to avoid circular dependency
def _get_models():
    from app.models.tenant.models import (
        Project, Dam, Component, Worker, DailyReading, ReadingDevice,
        DamReading, MaintenancePlan, WorkOrder, TenantUser, Asset,
        Warehouse, InventoryItem, InventoryTransaction, ReadingStatus
    )
    return locals()


# ══════════════════════════════════════════════════════════════
# PROJECTS
# ══════════════════════════════════════════════════════════════
@router.get("/projects")
def list_projects(db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Project
    return db.query(Project).filter(Project.is_deleted == False, Project.is_active == True).all()


@router.post("/projects")
def create_project(data: dict = Body(...), db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Project
    proj = Project(**{k: v for k, v in data.items() if hasattr(Project, k)})
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Project
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return p


# ══════════════════════════════════════════════════════════════
# DAMS & PHASES
# ══════════════════════════════════════════════════════════════
@router.get("/projects/{project_id}/dams")
def list_dams(project_id: int, db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Dam
    return db.query(Dam).filter(Dam.project_id == project_id, Dam.is_deleted == False).order_by(Dam.sort_order).all()


@router.post("/projects/{project_id}/dams")
def create_dam(project_id: int, data: dict = Body(...), db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Dam
    data["project_id"] = project_id
    dam = Dam(**{k: v for k, v in data.items() if hasattr(Dam, k)})
    db.add(dam)
    db.commit()
    db.refresh(dam)
    return dam


@router.get("/dams/{dam_id}/components")
def list_components(dam_id: int, db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Component
    return db.query(Component).filter(Component.dam_id == dam_id, Component.is_deleted == False).order_by(Component.sort_order).all()


@router.post("/dams/{dam_id}/components")
def create_component(dam_id: int, data: dict = Body(...), db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Component, Dam
    dam = db.query(Dam).filter(Dam.id == dam_id).first()
    if not dam:
        raise HTTPException(404, "Dam not found")
    data["dam_id"] = dam_id
    # Auto-generate code if not provided
    if "code" not in data:
        count = db.query(Component).filter(Component.dam_id == dam_id).count()
        data["code"] = f"{dam.code}-{count+1:03d}"

    comp = Component(**{k: v for k, v in data.items() if hasattr(Component, k)})
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp


@router.post("/dams/{dam_id}/upload-storage-curve")
async def upload_storage_curve(
    dam_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(lambda: None),
):
    """Upload Excel file with level-storage curve"""
    from app.models.tenant.models import Dam
    import openpyxl

    dam = db.query(Dam).filter(Dam.id == dam_id).first()
    if not dam:
        raise HTTPException(404)

    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb.active

    curve = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is not None and row[1] is not None:
            try:
                curve.append({
                    "level": float(row[0]),      # منسوب بالمتر
                    "volume_mcm": float(row[1])  # حجم بالمليون متر مكعب
                })
            except (TypeError, ValueError):
                continue

    dam.storage_curve = sorted(curve, key=lambda x: x["level"])
    db.commit()

    return {
        "dam_id": dam_id,
        "points_loaded": len(curve),
        "level_range": f"{curve[0]['level']} — {curve[-1]['level']} م" if curve else "N/A",
    }


# ══════════════════════════════════════════════════════════════
# WORKERS (Technical Staff)
# ══════════════════════════════════════════════════════════════
@router.get("/workers")
def list_workers(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(lambda: None),
):
    from app.models.tenant.models import Worker
    q = db.query(Worker).filter(Worker.is_deleted == False, Worker.is_active == True)
    if project_id:
        q = q.filter(Worker.project_id == project_id)
    if status:
        q = q.filter(Worker.status == status)
    return q.all()


@router.post("/workers")
def create_worker(data: dict = Body(...), db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Worker
    worker = Worker(**{k: v for k, v in data.items() if hasattr(Worker, k)})
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.get("/workers/{worker_id}")
def get_worker(worker_id: int, db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Worker
    w = db.query(Worker).filter(Worker.id == worker_id).first()
    if not w:
        raise HTTPException(404)
    return w


@router.get("/workers/expiring-documents")
def expiring_documents(days: int = 30, db: Session = Depends(lambda: None)):
    """Get workers with documents expiring within N days"""
    from app.models.tenant.models import Worker
    threshold = date.today() + timedelta(days=days)
    workers = db.query(Worker).filter(
        Worker.document_expiry <= threshold,
        Worker.document_expiry >= date.today(),
        Worker.is_active == True,
        Worker.is_deleted == False,
    ).all()
    return workers


@router.patch("/workers/{worker_id}/leave")
def update_worker_leave(
    worker_id: int,
    leave_start: date = Body(...),
    leave_end: date = Body(...),
    db: Session = Depends(lambda: None),
):
    from app.models.tenant.models import Worker, WorkerStatus
    w = db.query(Worker).filter(Worker.id == worker_id).first()
    if not w:
        raise HTTPException(404)
    w.last_leave_start = leave_start
    w.last_leave_end = leave_end
    w.return_from_leave = leave_end + timedelta(days=1)
    w.status = WorkerStatus.on_leave
    db.commit()
    return w


# ══════════════════════════════════════════════════════════════
# READING DEVICES
# ══════════════════════════════════════════════════════════════
@router.get("/reading-devices")
def list_devices(project_id: Optional[int] = None, db: Session = Depends(lambda: None)):
    from app.models.tenant.models import ReadingDevice
    q = db.query(ReadingDevice).filter(ReadingDevice.is_deleted == False)
    if project_id:
        q = q.filter(ReadingDevice.project_id == project_id)
    return q.all()


@router.post("/reading-devices")
def create_device(data: dict = Body(...), db: Session = Depends(lambda: None)):
    from app.models.tenant.models import ReadingDevice
    dev = ReadingDevice(**{k: v for k, v in data.items() if hasattr(ReadingDevice, k)})
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev


# ══════════════════════════════════════════════════════════════
# DAILY READINGS
# ══════════════════════════════════════════════════════════════
@router.get("/readings")
def list_readings(
    project_id: Optional[int] = None,
    device_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(lambda: None),
):
    from app.models.tenant.models import DailyReading
    q = db.query(DailyReading)
    if project_id:
        q = q.filter(DailyReading.project_id == project_id)
    if device_id:
        q = q.filter(DailyReading.device_id == device_id)
    if from_date:
        q = q.filter(DailyReading.reading_datetime >= from_date)
    if to_date:
        q = q.filter(DailyReading.reading_datetime <= to_date)
    return q.order_by(DailyReading.reading_datetime.desc()).limit(500).all()


@router.post("/readings")
def create_reading(data: dict = Body(...), db: Session = Depends(lambda: None)):
    from app.models.tenant.models import DailyReading, ReadingDevice, ReadingStatus
    from app.services.smart_scheduler import calculate_storage_from_level

    # Get device to check limits and storage curve
    device_id = data.get("device_id")
    device = db.query(ReadingDevice).filter(ReadingDevice.id == device_id).first()

    value = float(data.get("value", 0))
    status = ReadingStatus.normal

    if device:
        if device.alarm_low and value <= device.alarm_low:
            status = ReadingStatus.alarm
        elif device.alarm_high and value >= device.alarm_high:
            status = ReadingStatus.alarm
        elif device.warning_low and value <= device.warning_low:
            status = ReadingStatus.warning
        elif device.warning_high and value >= device.warning_high:
            status = ReadingStatus.warning

        # Compute storage if device has curve
        computed_value = None
        computed_unit = None
        if device.has_storage_curve and device.storage_curve_data:
            computed_value = calculate_storage_from_level(value, device.storage_curve_data)
            if computed_value is not None:
                computed_value = round(computed_value, 3)
                computed_unit = "م م³"

        data["status"] = status
        data["computed_value"] = computed_value
        data["computed_unit"] = computed_unit

    reading = DailyReading(**{k: v for k, v in data.items() if hasattr(DailyReading, k)})
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/readings/alerts")
def reading_alerts(project_id: Optional[int] = None, db: Session = Depends(lambda: None)):
    """Get readings with warning or alarm status from last 24 hours"""
    from app.models.tenant.models import DailyReading, ReadingStatus
    from datetime import datetime, timezone

    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    q = db.query(DailyReading).filter(
        DailyReading.status.in_([ReadingStatus.warning, ReadingStatus.alarm, ReadingStatus.critical]),
        DailyReading.reading_datetime >= yesterday,
    )
    if project_id:
        q = q.filter(DailyReading.project_id == project_id)
    return q.order_by(DailyReading.reading_datetime.desc()).all()


# ══════════════════════════════════════════════════════════════
# DAM READINGS (Full Geotechnical)
# ══════════════════════════════════════════════════════════════
@router.get("/dam-readings")
def list_dam_readings(dam_id: int, from_date: Optional[date] = None, to_date: Optional[date] = None, db: Session = Depends(lambda: None)):
    from app.models.tenant.models import DamReading
    q = db.query(DamReading).filter(DamReading.dam_id == dam_id)
    if from_date:
        q = q.filter(DamReading.reading_date >= from_date)
    if to_date:
        q = q.filter(DamReading.reading_date <= to_date)
    return q.order_by(DamReading.reading_date.desc()).limit(365).all()


@router.post("/dam-readings")
def create_dam_reading(data: dict = Body(...), db: Session = Depends(lambda: None)):
    from app.models.tenant.models import DamReading, Dam, ReadingStatus
    from app.services.smart_scheduler import calculate_storage_from_level

    dam = db.query(Dam).filter(Dam.id == data.get("dam_id")).first()

    # Auto-calculate storage from level if dam has curve
    if dam and dam.storage_curve and data.get("upstream_level"):
        vol = calculate_storage_from_level(data["upstream_level"], dam.storage_curve)
        if vol:
            data["storage_volume_mcm"] = round(vol, 3)

    # Determine overall status
    status = ReadingStatus.normal
    if dam:
        level = data.get("upstream_level", 0)
        if dam.flood_pool_level and level >= dam.flood_pool_level:
            status = ReadingStatus.alarm
        elif dam.normal_pool_level and level >= dam.normal_pool_level * 0.95:
            status = ReadingStatus.warning
    data["overall_status"] = status

    reading = DamReading(**{k: v for k, v in data.items() if hasattr(DamReading, k)})
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


# ══════════════════════════════════════════════════════════════
# SMART MAINTENANCE GENERATION
# ══════════════════════════════════════════════════════════════
@router.post("/maintenance-plans/{plan_id}/generate-smart")
def generate_smart_work_orders(
    plan_id: int,
    max_per_day: int = Query(5, ge=1, le=20),
    db: Session = Depends(lambda: None),
):
    from app.models.tenant.models import MaintenancePlan, WorkOrder, Project, WorkOrderType, WorkOrderStatus, WorkOrderPriority
    from app.services.smart_scheduler import generate_work_orders_for_plan

    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")

    project = db.query(Project).filter(Project.id == plan.project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    # Delete existing pending WOs for this plan (regenerate)
    db.query(WorkOrder).filter(
        WorkOrder.maintenance_plan_id == plan_id,
        WorkOrder.status == WorkOrderStatus.pending,
    ).delete()

    wo_data_list, stats = generate_work_orders_for_plan(
        plan_id=plan_id,
        plan_name=plan.name,
        frequency=plan.frequency.value if hasattr(plan.frequency, 'value') else str(plan.frequency),
        project_start=project.start_date or date.today(),
        project_end=project.end_date or date(date.today().year + 2, 12, 31),
        component_id=plan.component_id,
        project_id=plan.project_id,
        estimated_duration=plan.estimated_duration_hours,
        estimated_cost=plan.estimated_cost,
        checklist_items=plan.checklist_items or [],
        max_wo_per_day=max_per_day,
    )

    # Bulk insert work orders
    created = 0
    for wo_data in wo_data_list:
        wo = WorkOrder(
            wo_number=wo_data["wo_number"],
            maintenance_plan_id=plan_id,
            title=wo_data["title"],
            title_ar=wo_data["title_ar"],
            wo_type=WorkOrderType.preventive,
            status=WorkOrderStatus.pending,
            priority=WorkOrderPriority.medium,
            project_id=wo_data["project_id"],
            component_id=wo_data["component_id"],
            scheduled_date=wo_data["scheduled_date"],
            estimated_duration_hours=wo_data["estimated_duration_hours"],
            estimated_cost=wo_data["estimated_cost"],
            checklist_completed=wo_data["checklist_items"],
            created_by_id=1,
        )
        db.add(wo)
        created += 1

    # Update plan
    if wo_data_list:
        plan.next_due_date = min(date.fromisoformat(str(w["scheduled_date"])) for w in wo_data_list)
        plan.last_generated_date = date.today()

    db.commit()

    return {
        "plan_id": plan_id,
        "frequency": plan.frequency,
        "work_orders_created": created,
        "schedule_stats": stats,
        "first_wo_date": str(wo_data_list[0]["scheduled_date"]) if wo_data_list else None,
        "last_wo_date": str(wo_data_list[-1]["scheduled_date"]) if wo_data_list else None,
    }


# ══════════════════════════════════════════════════════════════
# WAREHOUSES & INVENTORY
# ══════════════════════════════════════════════════════════════
@router.get("/warehouses")
def list_warehouses(db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Warehouse
    return db.query(Warehouse).filter(Warehouse.is_deleted == False).all()


@router.post("/warehouses")
def create_warehouse(data: dict = Body(...), db: Session = Depends(lambda: None)):
    from app.models.tenant.models import Warehouse
    wh = Warehouse(**{k: v for k, v in data.items() if hasattr(Warehouse, k)})
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


@router.get("/warehouses/{wh_id}/items")
def warehouse_items(wh_id: int, db: Session = Depends(lambda: None)):
    from app.models.tenant.models import InventoryItem
    return db.query(InventoryItem).filter(
        InventoryItem.warehouse_id == wh_id,
        InventoryItem.is_deleted == False,
    ).all()


@router.get("/inventory/low-stock")
def low_stock_items(db: Session = Depends(lambda: None)):
    from app.models.tenant.models import InventoryItem
    return db.query(InventoryItem).filter(
        InventoryItem.quantity_in_stock <= InventoryItem.reorder_point,
        InventoryItem.is_deleted == False,
    ).all()


@router.post("/inventory/transaction")
def inventory_transaction(
    item_id: int,
    quantity: float,
    tx_type: str,  # in, out, transfer, adjustment
    warehouse_id: int,
    reference_number: str = "",
    notes: str = "",
    performed_by_id: int = 1,
    to_warehouse_id: Optional[int] = None,
    db: Session = Depends(lambda: None),
):
    from app.models.tenant.models import InventoryItem, InventoryTransaction

    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(404)

    qty_before = item.quantity_in_stock

    if tx_type == "out":
        if item.quantity_in_stock < quantity:
            raise HTTPException(400, f"Insufficient stock: {item.quantity_in_stock} < {quantity}")
        item.quantity_in_stock -= quantity
    elif tx_type == "in":
        item.quantity_in_stock += quantity
        item.last_restock_date = date.today()
    elif tx_type == "transfer" and to_warehouse_id:
        if item.quantity_in_stock < quantity:
            raise HTTPException(400, "Insufficient stock for transfer")
        item.quantity_in_stock -= quantity
    elif tx_type == "adjustment":
        item.quantity_in_stock = quantity

    item.total_value = item.quantity_in_stock * item.unit_cost

    tx = InventoryTransaction(
        item_id=item_id,
        warehouse_id=warehouse_id,
        transaction_type=tx_type,
        quantity=quantity,
        quantity_before=qty_before,
        quantity_after=item.quantity_in_stock,
        unit_cost=item.unit_cost,
        total_cost=quantity * item.unit_cost,
        reference_number=reference_number,
        to_warehouse_id=to_warehouse_id,
        performed_by_id=performed_by_id,
        notes=notes,
    )
    db.add(tx)
    db.commit()
    return {"item": item, "transaction": tx}
