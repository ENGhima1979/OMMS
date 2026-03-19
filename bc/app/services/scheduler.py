"""
OMMS Scheduler Service
Automated tasks: generate WOs from plans, send alerts, check overdue items
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
import logging

logger = logging.getLogger("omms.scheduler")
scheduler = AsyncIOScheduler()


def get_db_session():
    from app.core.database import SessionLocal
    return SessionLocal()


async def auto_generate_work_orders():
    """Daily: Generate work orders for plans due in next 3 days"""
    from app.models.models import (
        MaintenancePlan, WorkOrder, WorkOrderType, WorkOrderStatus, Notification
    )
    from app.models.models import MaintenanceFrequency

    db = get_db_session()
    try:
        today = date.today()
        trigger_date = today + timedelta(days=3)

        plans = db.query(MaintenancePlan).filter(
            MaintenancePlan.is_active == True,
            MaintenancePlan.next_due_date <= trigger_date,
            MaintenancePlan.next_due_date >= today,
        ).all()

        freq_days = {
            MaintenanceFrequency.daily: 1, MaintenanceFrequency.weekly: 7,
            MaintenanceFrequency.biweekly: 14, MaintenanceFrequency.monthly: 30,
            MaintenanceFrequency.quarterly: 90, MaintenanceFrequency.semi_annual: 180,
            MaintenanceFrequency.annual: 365,
        }

        generated = 0
        for plan in plans:
            # Check if WO already exists for this plan/date
            existing = db.query(WorkOrder).filter(
                WorkOrder.maintenance_plan_id == plan.id,
                WorkOrder.scheduled_date == plan.next_due_date,
                WorkOrder.status.notin_([WorkOrderStatus.cancelled]),
            ).first()

            if not existing:
                count = db.query(WorkOrder).count()
                wo = WorkOrder(
                    wo_number=f"PM-{today.year}-{count+1:06d}",
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
                    created_by_id=1,
                    checklist_completed=plan.checklist_items,
                )
                db.add(wo)

                # Update plan next due date
                days = plan.custom_days if plan.frequency == MaintenanceFrequency.custom else freq_days.get(plan.frequency, 30)
                plan.next_due_date = plan.next_due_date + timedelta(days=days)
                generated += 1

        db.commit()
        if generated:
            logger.info(f"Auto-generated {generated} work orders")

    except Exception as e:
        logger.error(f"Error in auto_generate_work_orders: {e}")
        db.rollback()
    finally:
        db.close()


async def check_overdue_work_orders():
    """Daily: Mark overdue work orders and create alerts"""
    from app.models.models import WorkOrder, WorkOrderStatus, Notification

    db = get_db_session()
    try:
        today = date.today()
        active = [WorkOrderStatus.pending, WorkOrderStatus.assigned, WorkOrderStatus.in_progress]

        overdue_wos = db.query(WorkOrder).filter(
            WorkOrder.scheduled_date < today,
            WorkOrder.status.in_(active),
            WorkOrder.is_overdue == False,
        ).all()

        for wo in overdue_wos:
            wo.is_overdue = True
            # Notify project manager (user_id=1 as default)
            notif = Notification(
                user_id=wo.assigned_to_id or 1,
                title=f"Overdue Work Order: {wo.wo_number}",
                title_ar=f"أمر عمل متأخر: {wo.wo_number}",
                message=f"Work order {wo.wo_number} is overdue since {wo.scheduled_date}",
                message_ar=f"أمر العمل {wo.wo_number} متأخر منذ {wo.scheduled_date}",
                notification_type="overdue_alert",
                reference_type="work_order",
                reference_id=wo.id,
            )
            db.add(notif)

        db.commit()
        if overdue_wos:
            logger.info(f"Marked {len(overdue_wos)} work orders as overdue")

    except Exception as e:
        logger.error(f"Error in check_overdue_work_orders: {e}")
        db.rollback()
    finally:
        db.close()


async def check_low_stock_alerts():
    """Daily: Check inventory low stock and alert"""
    from app.models.models import SparePart, Notification

    db = get_db_session()
    try:
        low_stock = db.query(SparePart).filter(
            SparePart.quantity_in_stock <= SparePart.reorder_point,
            SparePart.is_deleted == False,
        ).all()

        for part in low_stock:
            notif = Notification(
                user_id=1,
                title=f"Low Stock Alert: {part.name}",
                title_ar=f"تنبيه نقص مخزون: {part.name_ar or part.name}",
                message=f"Part {part.part_number} is below reorder point. Current: {part.quantity_in_stock}, Reorder at: {part.reorder_point}",
                message_ar=f"القطعة {part.part_number} أقل من نقطة إعادة الطلب. الحالي: {part.quantity_in_stock}",
                notification_type="inventory_alert",
                reference_type="spare_part",
                reference_id=part.id,
            )
            db.add(notif)

        db.commit()
        if low_stock:
            logger.info(f"Sent {len(low_stock)} low-stock alerts")

    except Exception as e:
        logger.error(f"Error in check_low_stock_alerts: {e}")
        db.rollback()
    finally:
        db.close()


async def check_contract_expiry():
    """Weekly: Alert for contracts expiring in 30 days"""
    from app.models.models import Contract, ContractStatus, Notification

    db = get_db_session()
    try:
        future = date.today() + timedelta(days=30)
        expiring = db.query(Contract).filter(
            Contract.end_date <= future,
            Contract.end_date >= date.today(),
            Contract.status == ContractStatus.active,
            Contract.is_deleted == False,
        ).all()

        for contract in expiring:
            days = (contract.end_date - date.today()).days
            notif = Notification(
                user_id=1,
                title=f"Contract Expiring: {contract.contract_number}",
                title_ar=f"عقد ينتهي قريباً: {contract.contract_number}",
                message=f"Contract {contract.contract_number} with {contract.party_name} expires in {days} days",
                message_ar=f"العقد {contract.contract_number} مع {contract.party_name} ينتهي خلال {days} يوم",
                notification_type="contract_expiry",
                reference_type="contract",
                reference_id=contract.id,
            )
            db.add(notif)

        db.commit()

    except Exception as e:
        logger.error(f"Error in check_contract_expiry: {e}")
        db.rollback()
    finally:
        db.close()


async def compute_kpi_snapshot():
    """Monthly: Save KPI snapshot for analytics"""
    from app.models.models import (
        KPISnapshot, Asset, AssetStatus, WorkOrder, WorkOrderStatus,
        WorkOrderType, SparePart, Incident, NonConformance, NonConformanceStatus
    )
    from sqlalchemy import func

    db = get_db_session()
    try:
        today = date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        total_assets = db.query(Asset).filter(Asset.is_deleted == False).count()
        operational = db.query(Asset).filter(Asset.status == AssetStatus.operational, Asset.is_deleted == False).count()
        availability = round(operational / total_assets * 100, 1) if total_assets else 0

        total_wo = db.query(WorkOrder).filter(WorkOrder.is_deleted == False).count()
        completed_wo = db.query(WorkOrder).filter(WorkOrder.status == WorkOrderStatus.completed).count()
        overdue_wo = db.query(WorkOrder).filter(
            WorkOrder.scheduled_date < today,
            WorkOrder.status.notin_([WorkOrderStatus.completed, WorkOrderStatus.cancelled])
        ).count()

        mttr = db.query(func.avg(WorkOrder.actual_duration_hours)).filter(
            WorkOrder.wo_type == WorkOrderType.corrective,
            WorkOrder.actual_duration_hours.isnot(None)
        ).scalar() or 0

        completion_rate = round(completed_wo / total_wo * 100, 1) if total_wo else 0
        oee = round(availability * completion_rate / 100, 1)

        snapshot = KPISnapshot(
            snapshot_date=today,
            period="monthly",
            total_assets=total_assets,
            assets_operational=operational,
            asset_availability_pct=availability,
            planned_wo_count=total_wo,
            completed_wo_count=completed_wo,
            overdue_wo_count=overdue_wo,
            wo_completion_rate=completion_rate,
            mttr_hours=round(float(mttr), 1),
            oee_pct=oee,
        )
        db.add(snapshot)
        db.commit()
        logger.info("KPI snapshot saved")

    except Exception as e:
        logger.error(f"Error in compute_kpi_snapshot: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    # Daily tasks at 6:00 AM
    scheduler.add_job(auto_generate_work_orders, CronTrigger(hour=6, minute=0), id="auto_gen_wo")
    scheduler.add_job(check_overdue_work_orders, CronTrigger(hour=6, minute=30), id="check_overdue")
    scheduler.add_job(check_low_stock_alerts, CronTrigger(hour=7, minute=0), id="low_stock")

    # Weekly (Monday)
    scheduler.add_job(check_contract_expiry, CronTrigger(day_of_week="mon", hour=8), id="contract_expiry")

    # Monthly (1st of month)
    scheduler.add_job(compute_kpi_snapshot, CronTrigger(day=1, hour=1), id="kpi_snapshot")

    scheduler.start()
    logger.info("Scheduler started with 5 jobs")


def stop_scheduler():
    scheduler.shutdown()
