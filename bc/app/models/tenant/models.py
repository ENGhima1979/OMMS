"""
OMMS Tenant Database Models — v3.0
نماذج قاعدة بيانات الشركة المستأجرة — كاملة مع كل الميزات الجديدة
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum as SAEnum, JSON, BigInteger, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

TenantBase = declarative_base()


# ── Enums ──────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    company_admin = "company_admin"
    project_manager = "project_manager"
    maintenance_engineer = "maintenance_engineer"
    field_technician = "field_technician"
    qa_inspector = "qa_inspector"
    store_keeper = "store_keeper"
    accountant = "accountant"
    data_entry = "data_entry"
    viewer = "viewer"


class ProjectType(str, enum.Enum):
    dam = "dam"
    water_treatment = "water_treatment"
    power_station = "power_station"
    industrial = "industrial"
    oil_gas = "oil_gas"
    building = "building"
    infrastructure = "infrastructure"
    wastewater = "wastewater"
    irrigation = "irrigation"


class AssetStatus(str, enum.Enum):
    operational = "operational"
    under_maintenance = "under_maintenance"
    out_of_service = "out_of_service"
    decommissioned = "decommissioned"
    standby = "standby"


class AssetType(str, enum.Enum):
    heavy_equipment = "heavy_equipment"
    tools = "tools"
    vehicle = "vehicle"
    electrical = "electrical"
    instrumentation = "instrumentation"
    civil = "civil"
    other = "other"


class WorkOrderStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    assigned = "assigned"
    in_progress = "in_progress"
    on_hold = "on_hold"
    completed = "completed"
    cancelled = "cancelled"
    verified = "verified"


class WorkOrderType(str, enum.Enum):
    preventive = "preventive"
    corrective = "corrective"
    emergency = "emergency"
    inspection = "inspection"
    calibration = "calibration"
    predictive = "predictive"


class WorkOrderPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class MaintenanceFrequency(str, enum.Enum):
    daily = "daily"          # 365/year
    weekly = "weekly"        # 52/year
    biweekly = "biweekly"    # 26/year
    monthly = "monthly"      # 12/year
    quarterly = "quarterly"  # 4/year
    semi_annual = "semi_annual"  # 2/year
    annual = "annual"        # 1/year
    custom = "custom"


class WorkerStatus(str, enum.Enum):
    available = "available"
    on_work_order = "on_work_order"
    on_leave = "on_leave"
    sick = "sick"
    suspended = "suspended"


class ReadingStatus(str, enum.Enum):
    normal = "normal"
    warning = "warning"
    critical = "critical"
    alarm = "alarm"


class DocumentType(str, enum.Enum):
    national_id = "national_id"
    iqama = "iqama"
    passport = "passport"


# ── Mixin ──────────────────────────────────────────────────────
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)


# ══════════════════════════════════════════════════════════════
# 1. USERS (Tenant)
# ══════════════════════════════════════════════════════════════
class TenantUser(TenantBase, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(30))
    whatsapp = Column(String(30))
    full_name = Column(String(200), nullable=False)
    full_name_ar = Column(String(200))
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.viewer)
    department = Column(String(100))
    job_title = Column(String(200))
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    language = Column(String(10), default="ar")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    project = relationship("Project", back_populates="users")
    assigned_work_orders = relationship("WorkOrder", foreign_keys="WorkOrder.assigned_to_id", back_populates="assigned_to")
    created_work_orders = relationship("WorkOrder", foreign_keys="WorkOrder.created_by_id", back_populates="created_by")


# ══════════════════════════════════════════════════════════════
# 2. PROJECTS → DAMS/PHASES → COMPONENTS
# ══════════════════════════════════════════════════════════════
class Project(TenantBase, TimestampMixin):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    description = Column(Text)
    project_type = Column(SAEnum(ProjectType), nullable=False, default=ProjectType.dam)
    location = Column(String(300))
    latitude = Column(Float)
    longitude = Column(Float)
    client_name = Column(String(300))
    client_name_ar = Column(String(300))
    contractor_name = Column(String(300))
    start_date = Column(Date)
    end_date = Column(Date)
    budget = Column(Float, default=0.0)
    currency = Column(String(10), default="SAR")
    is_active = Column(Boolean, default=True)
    project_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    settings = Column(JSON, default={})

    users = relationship("TenantUser", back_populates="project")
    dams = relationship("Dam", back_populates="project")
    work_orders = relationship("WorkOrder", back_populates="project")
    maintenance_plans = relationship("MaintenancePlan", back_populates="project")
    budget_plans = relationship("BudgetPlan", back_populates="project")
    daily_readings = relationship("DailyReading", back_populates="project")
    incidents = relationship("Incident", back_populates="project")


class Dam(TenantBase, TimestampMixin):
    """سد أو مرحلة داخل المشروع"""
    __tablename__ = "dams"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    code = Column(String(100), nullable=False)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    dam_type = Column(String(50), default="main")  # main, auxiliary, phase, canal
    description = Column(Text)
    # Dam specific
    dam_height_m = Column(Float)        # ارتفاع السد بالمتر
    crest_elevation_m = Column(Float)   # منسوب التاج
    normal_pool_level = Column(Float)   # منسوب التخزين العادي
    flood_pool_level = Column(Float)    # منسوب الفيضان
    dead_pool_level = Column(Float)     # منسوب التخزين الميت
    catchment_area_km2 = Column(Float)  # مساحة حوض التصريف
    # Storage curve (Excel upload)
    storage_curve = Column(JSON, default=[])  # [{elevation: 140, volume_mcm: 45.2}, ...]
    latitude = Column(Float)
    longitude = Column(Float)
    sort_order = Column(Integer, default=0)

    project = relationship("Project", back_populates="dams")
    components = relationship("Component", back_populates="dam")
    dam_readings = relationship("DamReading", back_populates="dam")


class Component(TenantBase, TimestampMixin):
    """مكون داخل السد/المرحلة — مُكوَّد"""
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    dam_id = Column(Integer, ForeignKey("dams.id"), nullable=False)
    code = Column(String(100), nullable=False)  # e.g. DAM-001-005
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    component_type = Column(String(100))  # gate, pump, generator, sensor, canal...
    description = Column(Text)
    manufacturer = Column(String(200))
    model = Column(String(200))
    serial_number = Column(String(200))
    installation_date = Column(Date)
    expected_life_years = Column(Float)
    specifications = Column(JSON, default={})
    location_in_dam = Column(String(300))
    criticality = Column(String(20), default="medium")  # low, medium, high, critical
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    dam = relationship("Dam", back_populates="components")
    maintenance_plans = relationship("MaintenancePlan", back_populates="component")
    work_orders = relationship("WorkOrder", back_populates="component")
    assets = relationship("Asset", back_populates="component")


# ══════════════════════════════════════════════════════════════
# 3. ASSETS (Contractor Equipment & Tools)
# ══════════════════════════════════════════════════════════════
class Asset(TenantBase, TimestampMixin):
    """أصول المقاول: معدات، أدوات، مركبات"""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(100), unique=True, nullable=False)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    asset_type = Column(SAEnum(AssetType), default=AssetType.heavy_equipment)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    # Asset details
    manufacturer = Column(String(200))
    model = Column(String(200))
    serial_number = Column(String(200))
    plate_number = Column(String(100))    # رقم اللوحة للمركبات
    chassis_number = Column(String(100))  # رقم الهيكل
    engine_number = Column(String(100))   # رقم المحرك
    year_of_manufacture = Column(Integer)
    purchase_date = Column(Date)
    purchase_cost = Column(Float)
    current_value = Column(Float)
    warranty_expiry = Column(Date)
    # Custodian (حارس الأصل / المستلم)
    custodian_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    custody_date = Column(Date)
    custody_notes = Column(Text)
    custody_document = Column(String(500))  # path to handover document
    # Status
    status = Column(SAEnum(AssetStatus), default=AssetStatus.operational)
    condition = Column(String(20), default="good")  # good, fair, poor, critical
    location = Column(String(300))
    running_hours = Column(Float, default=0.0)
    odometer_km = Column(Float)
    last_maintenance_date = Column(Date)
    next_maintenance_date = Column(Date)
    qr_code = Column(Text)
    notes = Column(Text)
    images = Column(JSON, default=[])
    specifications = Column(JSON, default={})

    component = relationship("Component", back_populates="assets")
    custodian = relationship("Worker", back_populates="assigned_assets")


# ══════════════════════════════════════════════════════════════
# 4. WORKFORCE (Technical Staff)
# ══════════════════════════════════════════════════════════════
class Worker(TenantBase, TimestampMixin):
    """الكادر الفني والعمالة"""
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True)
    full_name = Column(String(200), nullable=False)
    full_name_ar = Column(String(200))
    # Identity documents
    document_type = Column(SAEnum(DocumentType), default=DocumentType.iqama)
    document_number = Column(String(100), unique=True)
    document_expiry = Column(Date)
    nationality = Column(String(50))
    passport_number = Column(String(100))
    # Work info
    specialization = Column(String(200))  # مهندس / فني ميكانيكي / كهربائي / سائق
    qualification = Column(String(200))   # بكالوريوس هندسة / دبلوم
    certifications = Column(JSON, default=[])  # قائمة بالشهادات المهنية
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    department = Column(String(100))
    # Leaves
    last_leave_start = Column(Date)
    last_leave_end = Column(Date)
    return_from_leave = Column(Date)
    annual_leave_balance = Column(Integer, default=30)
    # Contact
    phone = Column(String(30))
    whatsapp = Column(String(30))
    emergency_contact = Column(String(100))
    # Status
    status = Column(SAEnum(WorkerStatus), default=WorkerStatus.available)
    is_active = Column(Boolean, default=True)
    hire_date = Column(Date)
    contract_end_date = Column(Date)
    photo_url = Column(String(500))
    notes = Column(Text)

    assigned_assets = relationship("Asset", back_populates="custodian")
    work_order_assignments = relationship("WorkOrder", foreign_keys="WorkOrder.worker_id", back_populates="assigned_worker")


# ══════════════════════════════════════════════════════════════
# 5. MAINTENANCE PLANS (Smart Scheduling)
# ══════════════════════════════════════════════════════════════
class MaintenancePlan(TenantBase, TimestampMixin):
    __tablename__ = "maintenance_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_number = Column(String(100), unique=True)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    project_id = Column(Integer, ForeignKey("projects.id"))
    dam_id = Column(Integer, ForeignKey("dams.id"), nullable=True)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=True)
    # Frequency
    frequency = Column(SAEnum(MaintenanceFrequency), nullable=False)
    custom_days = Column(Integer)  # for custom frequency
    times_per_year = Column(Integer)  # calculated from frequency
    # Planning
    start_date = Column(Date)
    end_date = Column(Date)
    next_due_date = Column(Date)
    last_generated_date = Column(Date)
    # Estimates
    estimated_duration_hours = Column(Float, default=2.0)
    estimated_cost = Column(Float, default=0.0)
    required_workers = Column(Integer, default=1)
    required_skills = Column(JSON, default=[])
    required_spare_parts = Column(JSON, default=[])
    # Checklist & Instructions
    checklist_items = Column(JSON, default=[])
    work_instructions = Column(Text)
    safety_precautions = Column(Text)
    standard_reference = Column(String(200))
    # Smart scheduling
    preferred_day_of_week = Column(Integer)    # 0=Sun ... 5=Fri
    preferred_time_of_day = Column(String(20)) # morning, afternoon, any
    max_per_day = Column(Integer, default=3)   # max WOs per day for this component
    is_active = Column(Boolean, default=True)
    notification_days_before = Column(Integer, default=7)

    project = relationship("Project", back_populates="maintenance_plans")
    component = relationship("Component", back_populates="maintenance_plans")
    work_orders = relationship("WorkOrder", back_populates="maintenance_plan")


# ══════════════════════════════════════════════════════════════
# 6. WORK ORDERS
# ══════════════════════════════════════════════════════════════
class WorkOrder(TenantBase, TimestampMixin):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    wo_number = Column(String(100), unique=True, nullable=False)
    title = Column(String(300), nullable=False)
    title_ar = Column(String(300))
    description = Column(Text)
    wo_type = Column(SAEnum(WorkOrderType), nullable=False)
    status = Column(SAEnum(WorkOrderStatus), default=WorkOrderStatus.draft)
    priority = Column(SAEnum(WorkOrderPriority), default=WorkOrderPriority.medium)
    # Relations
    project_id = Column(Integer, ForeignKey("projects.id"))
    dam_id = Column(Integer, ForeignKey("dams.id"), nullable=True)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=True)
    maintenance_plan_id = Column(Integer, ForeignKey("maintenance_plans.id"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Schedule
    scheduled_date = Column(Date)
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))
    estimated_duration_hours = Column(Float)
    actual_duration_hours = Column(Float)
    # Costs
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    material_cost = Column(Float, default=0.0)
    # Completion
    checklist_completed = Column(JSON, default=[])
    findings = Column(Text)
    corrective_actions = Column(Text)
    completion_notes = Column(Text)
    spare_parts_used = Column(JSON, default=[])
    images = Column(JSON, default=[])
    # PTW
    ptw_number = Column(String(100))
    requires_shutdown = Column(Boolean, default=False)
    safety_measures = Column(Text)
    # Flags
    is_overdue = Column(Boolean, default=False)
    failure_cause = Column(String(300))

    project = relationship("Project", back_populates="work_orders")
    component = relationship("Component", back_populates="work_orders")
    maintenance_plan = relationship("MaintenancePlan", back_populates="work_orders")
    assigned_to = relationship("TenantUser", foreign_keys=[assigned_to_id], back_populates="assigned_work_orders")
    created_by = relationship("TenantUser", foreign_keys=[created_by_id], back_populates="created_work_orders")
    assigned_worker = relationship("Worker", foreign_keys=[worker_id], back_populates="work_order_assignments")


# ══════════════════════════════════════════════════════════════
# 7. DAILY READINGS (Geotechnical & Operational)
# ══════════════════════════════════════════════════════════════
class ReadingDevice(TenantBase, TimestampMixin):
    """جهاز القراءة — بيزومتر، مقياس تدفق، الخ"""
    __tablename__ = "reading_devices"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    dam_id = Column(Integer, ForeignKey("dams.id"), nullable=True)
    code = Column(String(100), nullable=False)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    device_type = Column(String(100))  # piezometer, flow_meter, pressure_gauge, thermometer, seismograph, settlement_gauge
    device_type_ar = Column(String(100))
    unit = Column(String(50))          # م, بار, م³/ساعة, °م, mm
    unit_ar = Column(String(50))
    location = Column(String(300))
    # Limits
    min_value = Column(Float)
    max_value = Column(Float)
    warning_low = Column(Float)        # حد التحذير الأدنى
    warning_high = Column(Float)       # حد التحذير الأعلى
    alarm_low = Column(Float)          # حد الإنذار الأدنى
    alarm_high = Column(Float)         # حد الإنذار الأعلى
    # Reading schedule
    reading_frequency = Column(String(20), default="daily")  # daily, weekly, monthly
    is_active = Column(Boolean, default=True)
    # For storage curve (dam level → volume)
    has_storage_curve = Column(Boolean, default=False)
    storage_curve_data = Column(JSON, default=[])  # [{level: 140.0, volume_mcm: 45.2}]

    readings = relationship("DailyReading", back_populates="device")


class DailyReading(TenantBase):
    """قراءة يومية مسجلة"""
    __tablename__ = "daily_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("reading_devices.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    reading_datetime = Column(DateTime(timezone=True), nullable=False)
    value = Column(Float, nullable=False)
    computed_value = Column(Float)      # مثلاً: التخزين المحسوب من المنسوب
    computed_unit = Column(String(50))  # م م³
    status = Column(SAEnum(ReadingStatus), default=ReadingStatus.normal)
    recorded_by_id = Column(Integer, ForeignKey("users.id"))
    notes = Column(Text)
    is_verified = Column(Boolean, default=False)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("ReadingDevice", back_populates="readings")
    project = relationship("Project", back_populates="daily_readings")


class DamReading(TenantBase):
    """قراءات السد الجيوتقنية المتعددة في نفس الوقت"""
    __tablename__ = "dam_readings"

    id = Column(Integer, primary_key=True, index=True)
    dam_id = Column(Integer, ForeignKey("dams.id"), nullable=False)
    reading_date = Column(Date, nullable=False)
    recorded_by_id = Column(Integer, ForeignKey("users.id"))
    # Water levels
    upstream_level = Column(Float)      # منسوب المياه خلف السد
    downstream_level = Column(Float)    # منسوب المياه أمام السد
    storage_volume_mcm = Column(Float)  # حجم التخزين م م³ (محسوب من الكيرف)
    inflow_rate = Column(Float)         # معدل الوارد م³/ثانية
    outflow_rate = Column(Float)        # معدل المنصرف م³/ثانية
    spillway_flow = Column(Float)       # تصريف المسيل
    # Structural monitoring
    crest_settlement_mm = Column(Float) # هبوط التاج بالملليمتر
    seepage_rate = Column(Float)        # معدل التسرب لتر/ثانية
    uplift_pressure = Column(Float)     # ضغط الرفع
    turbidity_ntu = Column(Float)       # العكارة
    # Weather
    rainfall_mm = Column(Float)         # هطول الأمطار
    temperature_c = Column(Float)       # درجة الحرارة
    # Status
    overall_status = Column(SAEnum(ReadingStatus), default=ReadingStatus.normal)
    notes = Column(Text)
    weather_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dam = relationship("Dam", back_populates="dam_readings")


# ══════════════════════════════════════════════════════════════
# 8. INVENTORY & WAREHOUSES
# ══════════════════════════════════════════════════════════════
class Warehouse(TenantBase, TimestampMixin):
    """مستودع"""
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True)
    name = Column(String(200), nullable=False)
    name_ar = Column(String(200))
    location = Column(String(300))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    keeper_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    capacity_m3 = Column(Float)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)

    items = relationship("InventoryItem", back_populates="warehouse")
    transactions = relationship("InventoryTransaction", back_populates="warehouse")


class ItemCategory(TenantBase):
    __tablename__ = "item_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    name_ar = Column(String(200))
    code = Column(String(50))
    parent_id = Column(Integer, ForeignKey("item_categories.id"), nullable=True)
    items = relationship("InventoryItem", back_populates="category")


class InventoryItem(TenantBase, TimestampMixin):
    """صنف في المخزن"""
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String(100), unique=True)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    category_id = Column(Integer, ForeignKey("item_categories.id"))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    unit = Column(String(50), default="pcs")
    quantity_in_stock = Column(Float, default=0.0)
    minimum_quantity = Column(Float, default=0.0)
    maximum_quantity = Column(Float)
    reorder_point = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    shelf_location = Column(String(100))
    supplier_name = Column(String(200))
    supplier_contact = Column(String(100))
    lead_time_days = Column(Integer, default=7)
    barcode = Column(String(200))
    is_critical = Column(Boolean, default=False)
    last_restock_date = Column(Date)
    specifications = Column(JSON, default={})
    images = Column(JSON, default=[])
    notes = Column(Text)

    category = relationship("ItemCategory", back_populates="items")
    warehouse = relationship("Warehouse", back_populates="items")
    transactions = relationship("InventoryTransaction", back_populates="item")


class InventoryTransaction(TenantBase):
    """حركة مخزون"""
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    transaction_type = Column(String(30))  # in, out, transfer, adjustment, return
    quantity = Column(Float, nullable=False)
    quantity_before = Column(Float)
    quantity_after = Column(Float)
    unit_cost = Column(Float)
    total_cost = Column(Float)
    reference_type = Column(String(50))    # work_order, purchase_order, transfer
    reference_id = Column(Integer)
    reference_number = Column(String(100))
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id"))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item = relationship("InventoryItem", back_populates="transactions")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id], back_populates="transactions")


class PurchaseOrder(TenantBase, TimestampMixin):
    """طلب شراء"""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)
    po_number = Column(String(100), unique=True)
    supplier_name = Column(String(200))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    status = Column(String(30), default="draft")
    total_amount = Column(Float, default=0.0)
    expected_delivery = Column(Date)
    notes = Column(Text)
    items = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ══════════════════════════════════════════════════════════════
# 9. HSE, QUALITY, BUDGET, NOTIFICATIONS
# ══════════════════════════════════════════════════════════════
class Incident(TenantBase, TimestampMixin):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    incident_number = Column(String(100), unique=True)
    title = Column(String(300))
    severity = Column(String(30))
    project_id = Column(Integer, ForeignKey("projects.id"))
    incident_date = Column(Date)
    location = Column(String(300))
    description = Column(Text)
    root_cause = Column(Text)
    corrective_actions = Column(Text)
    status = Column(String(30), default="open")
    lost_time_hours = Column(Float, default=0.0)
    reported_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("Project", back_populates="incidents")


class BudgetPlan(TenantBase, TimestampMixin):
    __tablename__ = "budget_plans"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    year = Column(Integer)
    total_budget = Column(Float, default=0.0)
    labor_budget = Column(Float, default=0.0)
    material_budget = Column(Float, default=0.0)
    contractor_budget = Column(Float, default=0.0)
    overhead_budget = Column(Float, default=0.0)
    contingency_budget = Column(Float, default=0.0)
    currency = Column(String(10), default="SAR")
    is_approved = Column(Boolean, default=False)
    approved_by_id = Column(Integer, nullable=True)
    project = relationship("Project", back_populates="budget_plans")


class Notification(TenantBase):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(300))
    title_ar = Column(String(300))
    message = Column(Text)
    notification_type = Column(String(50))
    reference_type = Column(String(50))
    reference_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    is_sent_email = Column(Boolean, default=False)
    is_sent_whatsapp = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KPISnapshot(TenantBase):
    __tablename__ = "kpi_snapshots"
    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date)
    period = Column(String(20))
    total_assets = Column(Integer, default=0)
    assets_operational = Column(Integer, default=0)
    asset_availability_pct = Column(Float, default=0.0)
    planned_wo_count = Column(Integer, default=0)
    completed_wo_count = Column(Integer, default=0)
    overdue_wo_count = Column(Integer, default=0)
    wo_completion_rate = Column(Float, default=0.0)
    mttr_hours = Column(Float, default=0.0)
    mtbf_hours = Column(Float, default=0.0)
    oee_pct = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
