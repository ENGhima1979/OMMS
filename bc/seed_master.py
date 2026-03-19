"""
OMMS SaaS Master Seed
تهيئة النظام الرئيسي ببيانات أولية
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from app.core.tenant.db_manager import master_engine, MasterSession, initialize_tenant_db
from app.models.master_models import MasterBase, Company, PricingPlan, Subscription, SuperAdminUser
from app.core.security import get_password_hash


def seed_master():
    print("🌱 Seeding OMMS SaaS Master Database...")
    MasterBase.metadata.create_all(bind=master_engine)
    db = MasterSession()

    try:
        # ── 1. PRICING PLANS ────────────────────────────────────
        if db.query(PricingPlan).count() == 0:
            plans = [
                PricingPlan(
                    name="basic", name_ar="الباقة الأساسية",
                    price_monthly=1500, price_annual=15000,
                    max_users=10, max_projects=3, max_assets=100,
                    features=["work_orders", "maintenance_plans", "basic_reports", "inventory"],
                    sort_order=1,
                ),
                PricingPlan(
                    name="professional", name_ar="الباقة الاحترافية",
                    price_monthly=6000, price_annual=60000,
                    max_users=50, max_projects=20, max_assets=500,
                    features=["work_orders", "maintenance_plans", "advanced_reports",
                              "inventory", "ai_analytics", "daily_readings",
                              "hse", "quality", "workforce", "pdf_export", "excel_export"],
                    sort_order=2,
                ),
                PricingPlan(
                    name="enterprise", name_ar="باقة المؤسسات",
                    price_monthly=19000, price_annual=190000,
                    max_users=999, max_projects=999, max_assets=9999,
                    features=["all_features", "separate_db", "scada_integration",
                              "custom_reports", "api_access", "dedicated_support",
                              "sla_guarantee", "multi_company"],
                    sort_order=3,
                ),
            ]
            for p in plans:
                db.add(p)
            db.flush()
            print("  ✅ Pricing plans created")

        # ── 2. SUPER ADMIN USER ──────────────────────────────────
        if db.query(SuperAdminUser).count() == 0:
            sa = SuperAdminUser(
                username="superadmin",
                email="sa@omms.system",
                full_name="مدير النظام العام",
                hashed_password=get_password_hash("sa123"),
                role="super_admin",
            )
            db.add(sa)
            db.flush()
            print("  ✅ Super admin created (superadmin/sa123)")

        # ── 3. DEMO COMPANIES ────────────────────────────────────
        demo_companies = [
            {
                "slug": "water_national",
                "name_ar": "شركة المياه الوطنية",
                "name_en": "National Water Company",
                "industry_type": "dam",
                "city": "جدة",
                "region": "مكة المكرمة",
                "email": "admin@water-national.sa",
                "plan": "professional",
                "admin_email": "admin@water-national.sa",
                "admin_pass": "admin123",
            },
            {
                "slug": "dams_group",
                "name_ar": "مجموعة السدود السعودية",
                "name_en": "Saudi Dams Group",
                "industry_type": "dam",
                "city": "الرياض",
                "region": "الرياض",
                "email": "admin@dams-group.sa",
                "plan": "enterprise",
                "admin_email": "admin@dams-group.sa",
                "admin_pass": "admin123",
            },
            {
                "slug": "energy_co",
                "name_ar": "شركة الطاقة المتجددة",
                "name_en": "Renewable Energy Co.",
                "industry_type": "power_station",
                "city": "الدمام",
                "region": "الشرقية",
                "email": "admin@energy-co.sa",
                "plan": "basic",
                "admin_email": "admin@energy-co.sa",
                "admin_pass": "admin123",
                "trial": True,
            },
        ]

        for cd in demo_companies:
            if db.query(Company).filter(Company.slug == cd["slug"]).first():
                continue

            company = Company(
                slug=cd["slug"],
                name_ar=cd["name_ar"],
                name_en=cd["name_en"],
                industry_type=cd["industry_type"],
                city=cd["city"],
                region=cd["region"],
                email=cd["email"],
                timezone="Asia/Riyadh",
                language="ar",
                currency="SAR",
            )
            db.add(company)
            db.flush()

            # Find plan
            plan = db.query(PricingPlan).filter(PricingPlan.name == cd["plan"]).first()

            # Create subscription
            today = date.today()
            status = "trial" if cd.get("trial") else "active"
            sub = Subscription(
                company_id=company.id,
                plan_id=plan.id,
                status=status,
                start_date=today,
                end_date=today + timedelta(days=30 if cd.get("trial") else 365),
                billing_cycle="monthly",
                amount=plan.price_monthly,
                current_users=0,
            )
            db.add(sub)

            # Create company admin
            admin = SuperAdminUser(
                company_id=company.id,
                username=cd["admin_email"].split("@")[0],
                email=cd["admin_email"],
                full_name=f"مدير {cd['name_ar']}",
                hashed_password=get_password_hash(cd["admin_pass"]),
                role="company_admin",
            )
            db.add(admin)

            # Initialize tenant DB
            ok = initialize_tenant_db(cd["slug"])
            if ok:
                company.db_initialized = True
                # Seed tenant data
                _seed_tenant(cd["slug"])

            db.flush()
            print(f"  ✅ Company: {cd['name_ar']} ({cd['slug']}) — {'Trial' if cd.get('trial') else 'Active'}")

        db.commit()
        print("\n✅ Master seeding complete!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  Super Admin:  superadmin / sa123")
        print("  Water Co.:    admin / admin123  → water_national")
        print("  Dams Group:   admin / admin123  → dams_group")
        print("  Energy Co.:   admin / admin123  → energy_co")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


def _seed_tenant(slug: str):
    """Seed a tenant DB with sample project, dams, components"""
    from app.core.tenant.db_manager import get_tenant_session
    from app.models.tenant.models import (
        TenantUser, Project, Dam, Component, Worker, ReadingDevice,
        Warehouse, InventoryItem, ItemCategory, UserRole, ProjectType,
        WorkerStatus, DocumentType, MaintenancePlan, MaintenanceFrequency, BudgetPlan,
    )
    from app.core.security import get_password_hash

    Session = get_tenant_session(slug)
    db = Session()

    try:
        # Users
        if db.query(TenantUser).count() == 0:
            users = [
                TenantUser(employee_id="EMP-001", username="admin", email=f"admin@{slug}.sa",
                           full_name="مدير الشركة", hashed_password=get_password_hash("admin123"),
                           role=UserRole.company_admin, is_active=True, language="ar"),
                TenantUser(employee_id="EMP-002", username="engineer", email=f"eng@{slug}.sa",
                           full_name="أحمد الراشدي", full_name_ar="أحمد الراشدي",
                           hashed_password=get_password_hash("eng123"),
                           role=UserRole.maintenance_engineer, is_active=True),
                TenantUser(employee_id="EMP-003", username="technician", email=f"tech@{slug}.sa",
                           full_name="خالد الزهراني",
                           hashed_password=get_password_hash("tech123"),
                           role=UserRole.field_technician, is_active=True),
            ]
            for u in users:
                db.add(u)
            db.flush()

        # Project
        if db.query(Project).count() == 0:
            project = Project(
                code=f"{slug.upper()}-001",
                name="سد الفرسان — مشروع التشغيل والصيانة",
                name_ar="مشروع تشغيل وصيانة سد الفرسان",
                project_type=ProjectType.dam,
                location="منطقة جازان، المملكة العربية السعودية",
                client_name="وزارة البيئة والمياه والزراعة",
                contractor_name="شركة متقدمة للتشغيل والصيانة",
                start_date=date(2024, 1, 1),
                end_date=date(2026, 12, 31),
                budget=5_000_000.0,
                is_active=True,
            )
            db.add(project)
            db.flush()

            # Dam
            dam = Dam(
                project_id=project.id,
                code="DAM-001",
                name="السد الرئيسي",
                name_ar="السد الرئيسي — Al-Farasan Main Dam",
                dam_type="main",
                dam_height_m=45.0,
                crest_elevation_m=200.0,
                normal_pool_level=190.0,
                flood_pool_level=195.0,
                dead_pool_level=155.0,
                catchment_area_km2=1250.0,
                storage_curve=[
                    {"level": 155, "volume_mcm": 0},
                    {"level": 160, "volume_mcm": 5.2},
                    {"level": 165, "volume_mcm": 12.5},
                    {"level": 170, "volume_mcm": 24.8},
                    {"level": 175, "volume_mcm": 41.3},
                    {"level": 180, "volume_mcm": 62.7},
                    {"level": 185, "volume_mcm": 89.4},
                    {"level": 190, "volume_mcm": 122.0},
                    {"level": 195, "volume_mcm": 161.5},
                ],
                sort_order=1,
            )
            db.add(dam)
            db.flush()

            # Components
            components_data = [
                ("DAM-001-001", "بوابة التصريف الرئيسية", "gate", "critical"),
                ("DAM-001-002", "مضخة المياه الرئيسية #1", "pump", "critical"),
                ("DAM-001-003", "مضخة المياه الرئيسية #2", "pump", "critical"),
                ("DAM-001-004", "مولد احتياطي 500 KVA", "generator", "critical"),
                ("DAM-001-005", "منظومة الكلورة", "chemical_dosing", "high"),
                ("DAM-001-006", "لوحة التحكم MCC-01", "electrical_panel", "high"),
                ("DAM-001-007", "حساسات مستوى المياه", "sensor", "high"),
                ("DAM-001-008", "نظام التهوية والتكييف", "hvac", "medium"),
            ]
            for code, name, ctype, crit in components_data:
                comp = Component(
                    dam_id=dam.id,
                    code=code,
                    name=name,
                    name_ar=name,
                    component_type=ctype,
                    criticality=crit,
                    is_active=True,
                )
                db.add(comp)
            db.flush()

            # Budget
            budget = BudgetPlan(
                project_id=project.id,
                year=2025,
                total_budget=800_000,
                labor_budget=300_000,
                material_budget=250_000,
                contractor_budget=150_000,
                overhead_budget=70_000,
                contingency_budget=30_000,
                is_approved=True,
            )
            db.add(budget)

        # Workers
        if db.query(Worker).count() == 0:
            workers = [
                Worker(employee_id="W-001", full_name="أحمد محمد الراشدي",
                       document_type=DocumentType.national_id,
                       document_number="1098765432",
                       document_expiry=date(2026, 8, 15),
                       nationality="سعودي",
                       specialization="مهندس صيانة",
                       status=WorkerStatus.available),
                Worker(employee_id="W-002", full_name="خالد سعد الزهراني",
                       document_type=DocumentType.iqama,
                       document_number="2187654321",
                       document_expiry=date(2025, 12, 20),
                       nationality="يمني",
                       specialization="فني ميكانيكي",
                       status=WorkerStatus.available),
                Worker(employee_id="W-003", full_name="محمد علي الغامدي",
                       document_type=DocumentType.iqama,
                       document_number="2256789012",
                       document_expiry=date(2025, 4, 10),  # Expiring soon!
                       nationality="مصري",
                       specialization="فني كهربائي",
                       status=WorkerStatus.available),
            ]
            for w in workers:
                db.add(w)
            db.flush()

        # Reading Devices
        if db.query(ReadingDevice).count() == 0:
            project = db.query(Project).first()
            dam = db.query(Dam).first()
            devices = [
                ReadingDevice(project_id=project.id, dam_id=dam.id,
                              code="PIZ-001", name="بيزومتر — منسوب المياه الرئيسي",
                              name_ar="بيزومتر P-01", device_type="piezometer",
                              device_type_ar="بيزومتر", unit="م", unit_ar="متر",
                              min_value=155, max_value=200,
                              warning_high=190, alarm_high=195,
                              reading_frequency="daily", has_storage_curve=True,
                              storage_curve_data=dam.storage_curve if dam else []),
                ReadingDevice(project_id=project.id,
                              code="PRESS-001", name="مقياس الضغط الرئيسي",
                              device_type="pressure_gauge", device_type_ar="مانومتر",
                              unit="بار",
                              min_value=0, max_value=10,
                              warning_high=4.5, alarm_high=5.0,
                              reading_frequency="daily"),
                ReadingDevice(project_id=project.id,
                              code="FLOW-001", name="عداد التدفق الرئيسي",
                              device_type="flow_meter", device_type_ar="عداد تدفق",
                              unit="م³/ساعة",
                              min_value=0, max_value=2000,
                              warning_low=100, warning_high=1800,
                              reading_frequency="daily"),
                ReadingDevice(project_id=project.id, dam_id=dam.id,
                              code="SEEP-001", name="مقياس التسرب",
                              device_type="seepage_meter", device_type_ar="مقياس تسرب",
                              unit="لتر/ثانية",
                              min_value=0, max_value=50,
                              warning_high=20, alarm_high=35,
                              reading_frequency="daily"),
            ]
            for d in devices:
                db.add(d)
            db.flush()

        # Warehouse
        if db.query(Warehouse).count() == 0:
            wh = Warehouse(code="WH-001", name="المستودع الرئيسي", name_ar="المستودع الرئيسي",
                           location="موقع السد — مبنى المخازن", is_active=True)
            db.add(wh)
            db.flush()

            cat = ItemCategory(name="قطع ميكانيكية", name_ar="قطع ميكانيكية", code="MECH")
            db.add(cat)
            db.flush()

            items = [
                InventoryItem(item_code="SP-00001", name="دفاعة مضخة 6 إنش", name_ar="دفاعة مضخة 6 إنش",
                              category_id=cat.id, warehouse_id=wh.id,
                              unit="قطعة", quantity_in_stock=2, minimum_quantity=3,
                              reorder_point=3, unit_cost=1200, total_value=2400, is_critical=True),
                InventoryItem(item_code="SP-00002", name="طقم حشوة المحور", name_ar="طقم حشوة المحور",
                              category_id=cat.id, warehouse_id=wh.id,
                              unit="طقم", quantity_in_stock=8, minimum_quantity=3,
                              reorder_point=4, unit_cost=450, total_value=3600, is_critical=True),
                InventoryItem(item_code="SP-00003", name="بيرينج 6208-2RS",
                              category_id=cat.id, warehouse_id=wh.id,
                              unit="قطعة", quantity_in_stock=24, minimum_quantity=10,
                              reorder_point=10, unit_cost=85, total_value=2040),
                InventoryItem(item_code="SP-00004", name="زيت هيدروليك 20 لتر",
                              category_id=cat.id, warehouse_id=wh.id,
                              unit="وحدة", quantity_in_stock=6, minimum_quantity=8,
                              reorder_point=8, unit_cost=150, total_value=900),
            ]
            for item in items:
                db.add(item)
            db.flush()

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"  ⚠️ Tenant seed error for {slug}: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_master()
