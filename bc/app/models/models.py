"""
OMMS Database Models
All SQLAlchemy ORM models for the system
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum as SAEnum, JSON, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    project_manager = "project_manager"
    maintenance_engineer = "maintenance_engineer"
    field_technician = "field_technician"
    qa_inspector = "qa_inspector"
    store_keeper = "store_keeper"
    accountant = "accountant"
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


class AssetStatus(str, enum.Enum):
    operational = "operational"
    under_maintenance = "under_maintenance"
    out_of_service = "out_of_service"
    decommissioned = "decommissioned"
    standby = "standby"


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
    predictive = "predictive"
    emergency = "emergency"
    inspection = "inspection"
    calibration = "calibration"


class WorkOrderPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"
    emergency = "emergency"


class MaintenanceFrequency(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    semi_annual = "semi_annual"
    annual = "annual"
    custom = "custom"


class PurchaseOrderStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    ordered = "ordered"
    received = "received"
    cancelled = "cancelled"


class ContractStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    expired = "expired"
    terminated = "terminated"
    renewal_due = "renewal_due"


class IncidentSeverity(str, enum.Enum):
    near_miss = "near_miss"
    minor = "minor"
    moderate = "moderate"
    major = "major"
    critical = "critical"
    fatal = "fatal"


class NonConformanceStatus(str, enum.Enum):
    open = "open"
    under_review = "under_review"
    corrective_action = "corrective_action"
    closed = "closed"


# ─────────────────────────────────────────────
# MIXIN
# ─────────────────────────────────────────────

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)


# ─────────────────────────────────────────────
# 1. USER & AUTH
# ─────────────────────────────────────────────

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20))
    whatsapp = Column(String(20))
    full_name = Column(String(200), nullable=False)
    full_name_ar = Column(String(200))
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.viewer)
    department = Column(String(100))
    job_title = Column(String(100))
    job_title_ar = Column(String(100))
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    language = Column(String(10), default="ar")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    project = relationship("Project", back_populates="users")
    assigned_work_orders = relationship("WorkOrder", foreign_keys="WorkOrder.assigned_to_id", back_populates="assigned_to")
    created_work_orders = relationship("WorkOrder", foreign_keys="WorkOrder.created_by_id", back_populates="created_by")
    approved_work_orders = relationship("WorkOrder", foreign_keys="WorkOrder.approved_by_id", back_populates="approved_by")
    audit_logs = relationship("AuditLog", back_populates="user")


# ─────────────────────────────────────────────
# 2. PROJECT
# ─────────────────────────────────────────────

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    description = Column(Text)
    project_type = Column(SAEnum(ProjectType), nullable=False)
    location = Column(String(300))
    latitude = Column(Float)
    longitude = Column(Float)
    client_name = Column(String(200))
    contractor_name = Column(String(200))
    start_date = Column(Date)
    end_date = Column(Date)
    budget = Column(Float, default=0.0)
    currency = Column(String(10), default="SAR")
    is_active = Column(Boolean, default=True)
    logo_url = Column(String(500))
    settings_json = Column(JSON, default={})

    users = relationship("User", back_populates="project")
    assets = relationship("Asset", back_populates="project")
    work_orders = relationship("WorkOrder", back_populates="project")
    maintenance_plans = relationship("MaintenancePlan", back_populates="project")
    contracts = relationship("Contract", back_populates="project")
    incidents = relationship("Incident", back_populates="project")


# ─────────────────────────────────────────────
# 3. ASSET MANAGEMENT
# ─────────────────────────────────────────────

class AssetCategory(Base, TimestampMixin):
    __tablename__ = "asset_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_ar = Column(String(200))
    code = Column(String(50), unique=True)
    parent_id = Column(Integer, ForeignKey("asset_categories.id"), nullable=True)
    icon = Column(String(100))
    description = Column(Text)

    children = relationship("AssetCategory", back_populates="parent")
    parent = relationship("AssetCategory", back_populates="children", remote_side="AssetCategory.id")
    assets = relationship("Asset", back_populates="category")


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(100), unique=True, index=True, nullable=False)
    qr_code = Column(String(500))
    barcode = Column(String(200))
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("asset_categories.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    parent_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    manufacturer = Column(String(200))
    model = Column(String(200))
    serial_number = Column(String(200))
    supplier = Column(String(200))
    purchase_date = Column(Date)
    installation_date = Column(Date)
    warranty_expiry = Column(Date)
    expected_life_years = Column(Float)
    purchase_cost = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    location = Column(String(300))
    location_detail = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    status = Column(SAEnum(AssetStatus), default=AssetStatus.operational)
    criticality = Column(String(20), default="medium")  # low, medium, high, critical
    specifications = Column(JSON, default={})
    documents = Column(JSON, default=[])
    images = Column(JSON, default=[])
    last_maintenance_date = Column(Date)
    next_maintenance_date = Column(Date)
    running_hours = Column(Float, default=0.0)
    total_downtime_hours = Column(Float, default=0.0)

    category = relationship("AssetCategory", back_populates="assets")
    project = relationship("Project", back_populates="assets")
    parent = relationship("Asset", remote_side="Asset.id", back_populates="children")
    children = relationship("Asset", back_populates="parent")
    maintenance_plans = relationship("MaintenancePlan", back_populates="asset")
    work_orders = relationship("WorkOrder", back_populates="asset")
    spare_parts = relationship("SparePart", back_populates="asset")


# ─────────────────────────────────────────────
# 4. MAINTENANCE PLANS
# ─────────────────────────────────────────────

class MaintenancePlan(Base, TimestampMixin):
    __tablename__ = "maintenance_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_number = Column(String(100), unique=True, index=True)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    description = Column(Text)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    frequency = Column(SAEnum(MaintenanceFrequency), nullable=False)
    custom_days = Column(Integer)  # For custom frequency
    estimated_duration_hours = Column(Float, default=1.0)
    estimated_cost = Column(Float, default=0.0)
    required_skills = Column(JSON, default=[])
    required_tools = Column(JSON, default=[])
    required_spare_parts = Column(JSON, default=[])
    checklist_items = Column(JSON, default=[])  # Detailed checklist
    safety_precautions = Column(Text)
    instructions = Column(Text)
    instructions_ar = Column(Text)
    is_active = Column(Boolean, default=True)
    start_date = Column(Date)
    next_due_date = Column(Date)
    last_executed_date = Column(Date)
    notification_days_before = Column(Integer, default=7)
    assigned_team = Column(JSON, default=[])
    standard_reference = Column(String(200))  # ISO, ASME, etc.

    asset = relationship("Asset", back_populates="maintenance_plans")
    project = relationship("Project", back_populates="maintenance_plans")
    work_orders = relationship("WorkOrder", back_populates="maintenance_plan")


# ─────────────────────────────────────────────
# 5. WORK ORDERS
# ─────────────────────────────────────────────

class WorkOrder(Base, TimestampMixin):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    wo_number = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(300), nullable=False)
    title_ar = Column(String(300))
    description = Column(Text)
    wo_type = Column(SAEnum(WorkOrderType), nullable=False)
    status = Column(SAEnum(WorkOrderStatus), default=WorkOrderStatus.draft)
    priority = Column(SAEnum(WorkOrderPriority), default=WorkOrderPriority.medium)
    project_id = Column(Integer, ForeignKey("projects.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"))
    maintenance_plan_id = Column(Integer, ForeignKey("maintenance_plans.id"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scheduled_date = Column(Date)
    scheduled_start_time = Column(DateTime(timezone=True))
    scheduled_end_time = Column(DateTime(timezone=True))
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))
    estimated_duration_hours = Column(Float)
    actual_duration_hours = Column(Float)
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    material_cost = Column(Float, default=0.0)
    checklist_completed = Column(JSON, default=[])
    findings = Column(Text)
    corrective_actions = Column(Text)
    technician_signature = Column(String(500))  # base64 signature
    supervisor_signature = Column(String(500))
    completion_notes = Column(Text)
    images = Column(JSON, default=[])
    documents = Column(JSON, default=[])
    spare_parts_used = Column(JSON, default=[])
    failure_cause = Column(String(300))
    failure_mode = Column(String(300))
    ptw_number = Column(String(100))  # Permit to Work
    requires_shutdown = Column(Boolean, default=False)
    safety_measures = Column(Text)
    is_overdue = Column(Boolean, default=False)

    project = relationship("Project", back_populates="work_orders")
    asset = relationship("Asset", back_populates="work_orders")
    maintenance_plan = relationship("MaintenancePlan", back_populates="work_orders")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_work_orders")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_work_orders")
    approved_by = relationship("User", foreign_keys=[approved_by_id], back_populates="approved_work_orders")


# ─────────────────────────────────────────────
# 6. INVENTORY / SPARE PARTS
# ─────────────────────────────────────────────

class SparePartCategory(Base, TimestampMixin):
    __tablename__ = "spare_part_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_ar = Column(String(200))
    code = Column(String(50))
    parent_id = Column(Integer, ForeignKey("spare_part_categories.id"), nullable=True)

    spare_parts = relationship("SparePart", back_populates="category")


class SparePart(Base, TimestampMixin):
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("spare_part_categories.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    unit = Column(String(50), default="pcs")  # pcs, kg, liter, meter
    quantity_in_stock = Column(Float, default=0.0)
    minimum_quantity = Column(Float, default=0.0)
    maximum_quantity = Column(Float)
    reorder_point = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    location_in_warehouse = Column(String(200))
    supplier_name = Column(String(200))
    supplier_code = Column(String(100))
    lead_time_days = Column(Integer, default=7)
    barcode = Column(String(200))
    images = Column(JSON, default=[])
    specifications = Column(JSON, default={})
    is_critical = Column(Boolean, default=False)
    last_restock_date = Column(Date)

    category = relationship("SparePartCategory", back_populates="spare_parts")
    asset = relationship("Asset", back_populates="spare_parts")
    inventory_transactions = relationship("InventoryTransaction", back_populates="spare_part")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="spare_part")


class InventoryTransaction(Base, TimestampMixin):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id"))
    transaction_type = Column(String(50))  # in, out, adjustment, transfer
    quantity = Column(Float, nullable=False)
    quantity_before = Column(Float)
    quantity_after = Column(Float)
    unit_cost = Column(Float)
    total_cost = Column(Float)
    reference_type = Column(String(50))  # work_order, purchase_order, manual
    reference_id = Column(Integer)
    notes = Column(Text)
    performed_by_id = Column(Integer, ForeignKey("users.id"))

    spare_part = relationship("SparePart", back_populates="inventory_transactions")


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(100), unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    supplier_name = Column(String(200))
    supplier_contact = Column(String(200))
    status = Column(SAEnum(PurchaseOrderStatus), default=PurchaseOrderStatus.draft)
    order_date = Column(Date)
    expected_delivery = Column(Date)
    actual_delivery = Column(Date)
    total_amount = Column(Float, default=0.0)
    currency = Column(String(10), default="SAR")
    notes = Column(Text)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    documents = Column(JSON, default=[])

    items = relationship("PurchaseOrderItem", back_populates="purchase_order")


class PurchaseOrderItem(Base, TimestampMixin):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id"))
    description = Column(String(500))
    quantity = Column(Float, nullable=False)
    unit = Column(String(50))
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float)
    quantity_received = Column(Float, default=0.0)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    spare_part = relationship("SparePart", back_populates="purchase_order_items")


# ─────────────────────────────────────────────
# 7. CONTRACTS
# ─────────────────────────────────────────────

class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String(100), unique=True, index=True)
    title = Column(String(300), nullable=False)
    title_ar = Column(String(300))
    project_id = Column(Integer, ForeignKey("projects.id"))
    contract_type = Column(String(100))  # maintenance, supply, service, construction
    party_name = Column(String(200))
    party_contact = Column(String(200))
    status = Column(SAEnum(ContractStatus), default=ContractStatus.active)
    start_date = Column(Date)
    end_date = Column(Date)
    value = Column(Float, default=0.0)
    currency = Column(String(10), default="SAR")
    payment_terms = Column(String(200))
    scope_of_work = Column(Text)
    sla_response_hours = Column(Float)  # Service Level Agreement
    sla_resolution_hours = Column(Float)
    penalty_clause = Column(Text)
    documents = Column(JSON, default=[])
    notification_days = Column(Integer, default=30)
    notes = Column(Text)

    project = relationship("Project", back_populates="contracts")


# ─────────────────────────────────────────────
# 8. HSE - HEALTH, SAFETY & ENVIRONMENT
# ─────────────────────────────────────────────

class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_number = Column(String(100), unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey("projects.id"))
    severity = Column(SAEnum(IncidentSeverity), nullable=False)
    incident_date = Column(DateTime(timezone=True))
    location = Column(String(300))
    involved_persons = Column(JSON, default=[])
    witnesses = Column(JSON, default=[])
    immediate_actions = Column(Text)
    root_cause = Column(Text)
    corrective_actions = Column(Text)
    preventive_measures = Column(Text)
    reported_by_id = Column(Integer, ForeignKey("users.id"))
    investigated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    investigation_date = Column(Date)
    is_closed = Column(Boolean, default=False)
    images = Column(JSON, default=[])
    documents = Column(JSON, default=[])
    lost_time_hours = Column(Float, default=0.0)
    medical_treatment_required = Column(Boolean, default=False)

    project = relationship("Project", back_populates="incidents")


class PermitToWork(Base, TimestampMixin):
    __tablename__ = "permits_to_work"

    id = Column(Integer, primary_key=True, index=True)
    ptw_number = Column(String(100), unique=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    permit_type = Column(String(100))  # hot_work, confined_space, electrical, etc.
    work_description = Column(Text)
    location = Column(String(300))
    requestor_id = Column(Integer, ForeignKey("users.id"))
    issuer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    valid_from = Column(DateTime(timezone=True))
    valid_to = Column(DateTime(timezone=True))
    hazards_identified = Column(JSON, default=[])
    precautions = Column(JSON, default=[])
    ppe_required = Column(JSON, default=[])
    is_approved = Column(Boolean, default=False)
    is_closed = Column(Boolean, default=False)
    closure_notes = Column(Text)


# ─────────────────────────────────────────────
# 9. QUALITY CONTROL
# ─────────────────────────────────────────────

class InspectionChecklist(Base, TimestampMixin):
    __tablename__ = "inspection_checklists"

    id = Column(Integer, primary_key=True, index=True)
    checklist_number = Column(String(100), unique=True)
    name = Column(String(300), nullable=False)
    name_ar = Column(String(300))
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    inspector_id = Column(Integer, ForeignKey("users.id"))
    inspection_date = Column(DateTime(timezone=True))
    items = Column(JSON, default=[])  # [{item, status, notes, photo}]
    overall_result = Column(String(50))  # pass, fail, conditional
    notes = Column(Text)
    signature = Column(String(500))
    images = Column(JSON, default=[])
    standard_reference = Column(String(200))

    project = relationship("Project")


class NonConformance(Base, TimestampMixin):
    __tablename__ = "non_conformances"

    id = Column(Integer, primary_key=True, index=True)
    ncr_number = Column(String(100), unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey("projects.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    detected_by_id = Column(Integer, ForeignKey("users.id"))
    detection_date = Column(Date)
    severity = Column(String(50))  # minor, major, critical
    status = Column(SAEnum(NonConformanceStatus), default=NonConformanceStatus.open)
    root_cause = Column(Text)
    corrective_action = Column(Text)
    preventive_action = Column(Text)
    target_close_date = Column(Date)
    actual_close_date = Column(Date)
    images = Column(JSON, default=[])
    documents = Column(JSON, default=[])


# ─────────────────────────────────────────────
# 10. BUDGET & COSTS
# ─────────────────────────────────────────────

class BudgetPlan(Base, TimestampMixin):
    __tablename__ = "budget_plans"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    year = Column(Integer, nullable=False)
    total_budget = Column(Float, default=0.0)
    labor_budget = Column(Float, default=0.0)
    material_budget = Column(Float, default=0.0)
    contractor_budget = Column(Float, default=0.0)
    overhead_budget = Column(Float, default=0.0)
    contingency_budget = Column(Float, default=0.0)
    currency = Column(String(10), default="SAR")
    monthly_breakdown = Column(JSON, default={})
    is_approved = Column(Boolean, default=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text)


class CostTransaction(Base, TimestampMixin):
    __tablename__ = "cost_transactions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    transaction_date = Column(Date)
    cost_type = Column(String(50))  # labor, material, contractor, overhead
    description = Column(String(500))
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="SAR")
    reference_number = Column(String(100))
    invoice_url = Column(String(500))
    notes = Column(Text)
    recorded_by_id = Column(Integer, ForeignKey("users.id"))


# ─────────────────────────────────────────────
# 11. NOTIFICATIONS & AUDIT
# ─────────────────────────────────────────────

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(300), nullable=False)
    title_ar = Column(String(300))
    message = Column(Text)
    message_ar = Column(Text)
    notification_type = Column(String(50))  # maintenance_due, wo_assigned, alert, etc.
    reference_type = Column(String(50))
    reference_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    is_sent_whatsapp = Column(Boolean, default=False)
    is_sent_email = Column(Boolean, default=False)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100))  # create, update, delete, login, etc.
    entity_type = Column(String(100))
    entity_id = Column(Integer)
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))

    user = relationship("User", back_populates="audit_logs")


# ─────────────────────────────────────────────
# 12. KPIs & REPORTS
# ─────────────────────────────────────────────

class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    snapshot_date = Column(Date, nullable=False)
    period = Column(String(20))  # daily, weekly, monthly
    # Asset KPIs
    total_assets = Column(Integer, default=0)
    assets_operational = Column(Integer, default=0)
    asset_availability_pct = Column(Float, default=0.0)
    # Maintenance KPIs
    planned_wo_count = Column(Integer, default=0)
    completed_wo_count = Column(Integer, default=0)
    overdue_wo_count = Column(Integer, default=0)
    wo_completion_rate = Column(Float, default=0.0)
    avg_repair_time_hours = Column(Float, default=0.0)
    mtbf_hours = Column(Float, default=0.0)  # Mean Time Between Failures
    mttr_hours = Column(Float, default=0.0)  # Mean Time To Repair
    oee_pct = Column(Float, default=0.0)     # Overall Equipment Effectiveness
    # Cost KPIs
    planned_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    cost_variance_pct = Column(Float, default=0.0)
    # Safety KPIs
    incident_count = Column(Integer, default=0)
    near_miss_count = Column(Integer, default=0)
    lost_time_hours = Column(Float, default=0.0)
    # Quality KPIs
    ncr_count = Column(Integer, default=0)
    inspection_pass_rate = Column(Float, default=0.0)
