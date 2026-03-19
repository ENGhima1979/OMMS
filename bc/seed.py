"""
OMMS - Database Seed Script
Creates initial data: admin user, sample project, assets, maintenance plans
تهيئة قاعدة البيانات ببيانات نموذجية
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.models import (
    User, Project, Asset, AssetCategory, SparePartCategory, SparePart,
    MaintenancePlan, WorkOrder, BudgetPlan, Notification,
    UserRole, ProjectType, AssetStatus, WorkOrderType, WorkOrderStatus,
    WorkOrderPriority, MaintenanceFrequency
)


def seed():
    print("🌱 Seeding OMMS Database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── 1. ADMIN USER ──────────────────────────────────────────
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                employee_id="EMP-001",
                username="admin",
                email="admin@omms.com",
                full_name="System Administrator",
                full_name_ar="مدير النظام",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.super_admin,
                department="IT",
                job_title="System Administrator",
                job_title_ar="مدير النظام",
                is_active=True,
                language="ar",
            )
            db.add(admin)

            eng = User(
                employee_id="EMP-002",
                username="engineer",
                email="engineer@omms.com",
                full_name="Ahmed Al-Rashidi",
                full_name_ar="أحمد الراشدي",
                hashed_password=get_password_hash("eng123"),
                role=UserRole.maintenance_engineer,
                department="Maintenance",
                job_title="Senior Maintenance Engineer",
                job_title_ar="مهندس صيانة أول",
                is_active=True,
                language="ar",
            )
            db.add(eng)

            tech = User(
                employee_id="EMP-003",
                username="technician",
                email="tech@omms.com",
                full_name="Khalid Al-Zahrani",
                full_name_ar="خالد الزهراني",
                hashed_password=get_password_hash("tech123"),
                role=UserRole.field_technician,
                department="Operations",
                job_title="Field Technician",
                job_title_ar="فني ميداني",
                is_active=True,
                language="ar",
            )
            db.add(tech)
            db.flush()
            print("  ✅ Users created")

        # ── 2. PROJECT ──────────────────────────────────────────────
        project = db.query(Project).filter(Project.code == "DAM-001").first()
        if not project:
            project = Project(
                code="DAM-001",
                name="Al-Farasan Dam O&M Project",
                name_ar="مشروع تشغيل وصيانة سد الفرسان",
                description="Comprehensive O&M for Al-Farasan Dam and water treatment facilities",
                project_type=ProjectType.dam,
                location="Jizan Region, Saudi Arabia",
                latitude=17.1,
                longitude=42.5,
                client_name="Ministry of Water - Western Region",
                contractor_name="Advanced O&M Solutions Co.",
                start_date=date(2024, 1, 1),
                end_date=date(2026, 12, 31),
                budget=5_000_000.0,
                currency="SAR",
                is_active=True,
            )
            db.add(project)
            db.flush()
            print("  ✅ Project created")

        # ── 3. ASSET CATEGORIES ─────────────────────────────────────
        cats = {}
        for code, name, name_ar in [
            ("MECH", "Mechanical Equipment", "المعدات الميكانيكية"),
            ("ELEC", "Electrical Equipment", "المعدات الكهربائية"),
            ("CIVIL", "Civil Structures", "المنشآت المدنية"),
            ("INST", "Instrumentation", "الأجهزة والقياسات"),
            ("HVAC", "HVAC Systems", "أنظمة التكييف والتهوية"),
        ]:
            cat = db.query(AssetCategory).filter(AssetCategory.code == code).first()
            if not cat:
                cat = AssetCategory(name=name, name_ar=name_ar, code=code)
                db.add(cat)
                db.flush()
            cats[code] = cat

        # ── 4. ASSETS ───────────────────────────────────────────────
        asset_data = [
            ("ASSET-DAM-00001", "Main Spillway Gate", "بوابة التصريف الرئيسية", "CIVIL", "critical", 1_200_000),
            ("ASSET-DAM-00002", "Primary Water Pump #1", "مضخة المياه الرئيسية #1", "MECH", "critical", 350_000),
            ("ASSET-DAM-00003", "Primary Water Pump #2", "مضخة المياه الرئيسية #2", "MECH", "critical", 350_000),
            ("ASSET-DAM-00004", "Backup Generator 500KVA", "مولد احتياطي 500 KVA", "ELEC", "critical", 280_000),
            ("ASSET-DAM-00005", "Water Level Sensor Array", "مجموعة حساسات مستوى المياه", "INST", "high", 45_000),
            ("ASSET-DAM-00006", "Control Panel MCC-01", "لوحة التحكم MCC-01", "ELEC", "high", 180_000),
            ("ASSET-DAM-00007", "Chlorination System", "منظومة الكلورة", "MECH", "high", 95_000),
            ("ASSET-DAM-00008", "HVAC Unit - Control Room", "وحدة تكييف غرفة التحكم", "HVAC", "medium", 35_000),
        ]

        assets_list = []
        for code, name, name_ar, cat_code, criticality, cost in asset_data:
            asset = db.query(Asset).filter(Asset.asset_code == code).first()
            if not asset:
                import qrcode, io, base64
                qr = qrcode.QRCode(version=1, box_size=6, border=2)
                qr.add_data(f"OMMS|{code}|{name}")
                qr.make(fit=True)
                img = qr.make_image()
                buf = io.BytesIO()
                img.save(buf, "PNG")
                qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

                asset = Asset(
                    asset_code=code,
                    name=name,
                    name_ar=name_ar,
                    category_id=cats[cat_code].id,
                    project_id=project.id,
                    manufacturer="Technical Equipment Co.",
                    status=AssetStatus.operational,
                    criticality=criticality,
                    purchase_cost=float(cost),
                    current_value=float(cost) * 0.8,
                    location="Dam Site - Zone A",
                    installation_date=date(2020, 6, 15),
                    warranty_expiry=date(2025, 6, 15),
                    expected_life_years=20.0,
                    running_hours=12500.0,
                    qr_code=qr_b64,
                )
                db.add(asset)
                db.flush()
            assets_list.append(asset)

        print("  ✅ Assets created")

        # ── 5. SPARE PARTS ──────────────────────────────────────────
        sp_cat = db.query(SparePartCategory).filter(SparePartCategory.name == "Mechanical Parts").first()
        if not sp_cat:
            sp_cat = SparePartCategory(name="Mechanical Parts", name_ar="قطع غيار ميكانيكية", code="MECH")
            db.add(sp_cat)
            db.flush()

        spare_parts_data = [
            ("SP-000001", "Pump Impeller 6-inch", "دفاعة مضخة 6 إنش", 3, 2, 2, 1200),
            ("SP-000002", "Shaft Seal Kit", "طقم حشوة المحور", 8, 5, 4, 450),
            ("SP-000003", "Bearing 6208-2RS", "بيرينج 6208-2RS", 12, 6, 6, 85),
            ("SP-000004", "V-Belt B-72", "سير B-72", 20, 10, 8, 35),
            ("SP-000005", "Filter Cartridge 10 Micron", "فلتر 10 ميكرون", 5, 4, 4, 180),
            ("SP-000006", "Gate Valve 3-inch", "محبس بوابة 3 إنش", 4, 2, 2, 320),
            ("SP-000007", "Pressure Gauge 0-10 bar", "مانومتر 0-10 بار", 6, 3, 3, 95),
            ("SP-000008", "Lubricating Oil 20L", "زيت تشحيم 20 لتر", 15, 8, 8, 150),
        ]

        for pnum, name, name_ar, qty, minq, reorder, cost in spare_parts_data:
            if not db.query(SparePart).filter(SparePart.part_number == pnum).first():
                sp = SparePart(
                    part_number=pnum,
                    name=name,
                    name_ar=name_ar,
                    category_id=sp_cat.id,
                    unit="pcs",
                    quantity_in_stock=float(qty),
                    minimum_quantity=float(minq),
                    reorder_point=float(reorder),
                    unit_cost=float(cost),
                    total_value=float(qty * cost),
                    location_in_warehouse="Shelf-A1",
                    supplier_name="Al-Rashidi Technical Supplies",
                    lead_time_days=7,
                    is_critical=True if pnum in ["SP-000001", "SP-000002"] else False,
                )
                db.add(sp)

        print("  ✅ Spare parts created")

        # ── 6. MAINTENANCE PLANS ────────────────────────────────────
        plan_data = [
            (assets_list[1], "Weekly Pump Inspection", "فحص المضخة الأسبوعي", MaintenanceFrequency.weekly, 2.0, 500),
            (assets_list[1], "Monthly Pump Service", "صيانة المضخة الشهرية", MaintenanceFrequency.monthly, 4.0, 1500),
            (assets_list[3], "Generator Monthly Test", "اختبار المولد الشهري", MaintenanceFrequency.monthly, 3.0, 800),
            (assets_list[3], "Generator Annual Service", "الصيانة السنوية للمولد", MaintenanceFrequency.annual, 16.0, 12000),
            (assets_list[0], "Spillway Gate Quarterly Inspection", "فحص بوابة التصريف ربع السنوي", MaintenanceFrequency.quarterly, 8.0, 5000),
            (assets_list[5], "MCC Panel Annual Inspection", "فحص لوحة التحكم السنوي", MaintenanceFrequency.annual, 12.0, 8000),
            (assets_list[6], "Chlorination System Weekly Check", "فحص منظومة الكلورة الأسبوعي", MaintenanceFrequency.weekly, 1.5, 300),
        ]

        freq_days = {
            MaintenanceFrequency.daily: 1, MaintenanceFrequency.weekly: 7,
            MaintenanceFrequency.biweekly: 14, MaintenanceFrequency.monthly: 30,
            MaintenanceFrequency.quarterly: 90, MaintenanceFrequency.semi_annual: 180,
            MaintenanceFrequency.annual: 365,
        }

        for i, (asset, name, name_ar, freq, dur, cost) in enumerate(plan_data):
            pnum = f"PM-{i+1:05d}"
            if not db.query(MaintenancePlan).filter(MaintenancePlan.plan_number == pnum).first():
                days = freq_days.get(freq, 30)
                next_due = date.today() + timedelta(days=days // 2)
                plan = MaintenancePlan(
                    plan_number=pnum,
                    name=name,
                    name_ar=name_ar,
                    asset_id=asset.id,
                    project_id=project.id,
                    frequency=freq,
                    estimated_duration_hours=dur,
                    estimated_cost=float(cost),
                    is_active=True,
                    start_date=date.today(),
                    next_due_date=next_due,
                    notification_days_before=7,
                    checklist_items=[
                        {"item": "Check oil level", "item_ar": "فحص مستوى الزيت", "required": True},
                        {"item": "Inspect for leaks", "item_ar": "فحص التسربات", "required": True},
                        {"item": "Check vibration", "item_ar": "فحص الاهتزاز", "required": True},
                        {"item": "Test emergency stop", "item_ar": "اختبار زر الإيقاف الطارئ", "required": True},
                    ],
                    safety_precautions="Follow LOTO procedure. Wear PPE.",
                    standard_reference="ISO 55001",
                )
                db.add(plan)

        db.flush()
        print("  ✅ Maintenance plans created")

        # ── 7. SAMPLE WORK ORDERS ───────────────────────────────────
        wo_data = [
            ("PM-2025-000001", "Weekly Pump Inspection - Pump #1", "الفحص الأسبوعي - مضخة #1",
             WorkOrderType.preventive, WorkOrderStatus.completed, WorkOrderPriority.medium,
             assets_list[1], date.today() - timedelta(days=3), 2.5, 620),
            ("PM-2025-000002", "Monthly Generator Test", "اختبار المولد الشهري",
             WorkOrderType.preventive, WorkOrderStatus.in_progress, WorkOrderPriority.high,
             assets_list[3], date.today(), 3.0, 0),
            ("CM-2025-000001", "Pump #2 Seal Replacement", "استبدال حشوة مضخة #2",
             WorkOrderType.corrective, WorkOrderStatus.pending, WorkOrderPriority.critical,
             assets_list[2], date.today() + timedelta(days=1), 5.0, 0),
            ("IN-2025-000001", "Spillway Gate Inspection", "فحص بوابة التصريف",
             WorkOrderType.inspection, WorkOrderStatus.pending, WorkOrderPriority.high,
             assets_list[0], date.today() + timedelta(days=5), 8.0, 0),
            ("PM-2025-000003", "Chlorination System Check", "فحص منظومة الكلورة",
             WorkOrderType.preventive, WorkOrderStatus.overdue if hasattr(WorkOrderStatus, 'overdue') else WorkOrderStatus.pending,
             WorkOrderPriority.medium, assets_list[6],
             date.today() - timedelta(days=2), 1.5, 0),
        ]

        for wnum, title, title_ar, wtype, wstatus, priority, asset, sched, dur, cost in wo_data:
            if not db.query(WorkOrder).filter(WorkOrder.wo_number == wnum).first():
                wo = WorkOrder(
                    wo_number=wnum,
                    title=title,
                    title_ar=title_ar,
                    wo_type=wtype,
                    status=wstatus,
                    priority=priority,
                    project_id=project.id,
                    asset_id=asset.id,
                    scheduled_date=sched,
                    estimated_duration_hours=dur,
                    estimated_cost=float(cost),
                    actual_cost=float(cost) if wstatus == WorkOrderStatus.completed else 0,
                    actual_duration_hours=dur if wstatus == WorkOrderStatus.completed else None,
                    created_by_id=1,
                    assigned_to_id=2,
                    is_overdue=sched < date.today() and wstatus not in [WorkOrderStatus.completed, WorkOrderStatus.cancelled],
                )
                db.add(wo)

        print("  ✅ Work orders created")

        # ── 8. BUDGET PLAN ──────────────────────────────────────────
        if not db.query(BudgetPlan).filter(BudgetPlan.project_id == project.id,
                                           BudgetPlan.year == date.today().year).first():
            budget = BudgetPlan(
                project_id=project.id,
                year=date.today().year,
                total_budget=800_000.0,
                labor_budget=300_000.0,
                material_budget=250_000.0,
                contractor_budget=150_000.0,
                overhead_budget=70_000.0,
                contingency_budget=30_000.0,
                currency="SAR",
                is_approved=True,
                approved_by_id=1,
            )
            db.add(budget)

        print("  ✅ Budget plan created")

        # ── 9. NOTIFICATIONS ────────────────────────────────────────
        notifs = [
            (1, "Overdue Work Order Alert", "تنبيه: أمر عمل متأخر", "alert"),
            (1, "Low Stock: Pump Impeller", "تنبيه: نقص مخزون دفاعة المضخة", "inventory_alert"),
            (2, "New Work Order Assigned", "تم تعيين أمر عمل جديد", "wo_assigned"),
        ]
        for uid, title, title_ar, ntype in notifs:
            notif = Notification(
                user_id=uid,
                title=title,
                title_ar=title_ar,
                message=title,
                message_ar=title_ar,
                notification_type=ntype,
                is_read=False,
            )
            db.add(notif)

        db.commit()
        print("\n✅ Database seeded successfully!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  Login credentials:")
        print("  Admin:      admin / admin123")
        print("  Engineer:   engineer / eng123")
        print("  Technician: technician / tech123")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
