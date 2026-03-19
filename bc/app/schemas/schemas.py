"""
OMMS Pydantic Schemas
Request/Response models for all API endpoints
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Any, Dict
from datetime import date, datetime
from app.models.models import (
    UserRole, ProjectType, AssetStatus, WorkOrderStatus, WorkOrderType,
    WorkOrderPriority, MaintenanceFrequency, PurchaseOrderStatus,
    ContractStatus, IncidentSeverity, NonConformanceStatus
)


# ─── BASE ───
class PaginationResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    data: List[Any]


# ─── AUTH ───
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ─── USER ───
class UserCreate(BaseModel):
    employee_id: Optional[str]
    username: str
    email: EmailStr
    phone: Optional[str]
    full_name: str
    full_name_ar: Optional[str]
    password: str
    role: UserRole = UserRole.viewer
    department: Optional[str]
    job_title: Optional[str]
    project_id: Optional[int]

class UserUpdate(BaseModel):
    email: Optional[EmailStr]
    phone: Optional[str]
    full_name: Optional[str]
    full_name_ar: Optional[str]
    role: Optional[UserRole]
    department: Optional[str]
    job_title: Optional[str]
    is_active: Optional[bool]
    language: Optional[str]

class UserResponse(BaseModel):
    id: int
    employee_id: Optional[str]
    username: str
    email: str
    full_name: str
    full_name_ar: Optional[str]
    role: UserRole
    department: Optional[str]
    job_title: Optional[str]
    is_active: bool
    language: str
    avatar_url: Optional[str]
    project_id: Optional[int]
    class Config:
        from_attributes = True


# ─── PROJECT ───
class ProjectCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str]
    description: Optional[str]
    project_type: ProjectType
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    client_name: Optional[str]
    contractor_name: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    budget: float = 0.0
    currency: str = "SAR"

class ProjectUpdate(BaseModel):
    name: Optional[str]
    name_ar: Optional[str]
    description: Optional[str]
    location: Optional[str]
    client_name: Optional[str]
    contractor_name: Optional[str]
    end_date: Optional[date]
    budget: Optional[float]
    is_active: Optional[bool]

class ProjectResponse(BaseModel):
    id: int
    code: str
    name: str
    name_ar: Optional[str]
    project_type: ProjectType
    location: Optional[str]
    client_name: Optional[str]
    budget: float
    currency: str
    is_active: bool
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: Optional[datetime]
    class Config:
        from_attributes = True


# ─── ASSET ───
class AssetCreate(BaseModel):
    asset_code: str
    name: str
    name_ar: Optional[str]
    description: Optional[str]
    category_id: Optional[int]
    project_id: int
    parent_asset_id: Optional[int]
    manufacturer: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    supplier: Optional[str]
    purchase_date: Optional[date]
    installation_date: Optional[date]
    warranty_expiry: Optional[date]
    expected_life_years: Optional[float]
    purchase_cost: float = 0.0
    location: Optional[str]
    location_detail: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    criticality: str = "medium"
    specifications: Optional[Dict] = {}

class AssetUpdate(BaseModel):
    name: Optional[str]
    name_ar: Optional[str]
    description: Optional[str]
    status: Optional[AssetStatus]
    location: Optional[str]
    warranty_expiry: Optional[date]
    running_hours: Optional[float]
    current_value: Optional[float]
    criticality: Optional[str]
    specifications: Optional[Dict]

class AssetResponse(BaseModel):
    id: int
    asset_code: str
    name: str
    name_ar: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    status: AssetStatus
    criticality: str
    location: Optional[str]
    purchase_cost: float
    current_value: float
    installation_date: Optional[date]
    warranty_expiry: Optional[date]
    last_maintenance_date: Optional[date]
    next_maintenance_date: Optional[date]
    running_hours: float
    project_id: int
    category_id: Optional[int]
    created_at: Optional[datetime]
    class Config:
        from_attributes = True


# ─── MAINTENANCE PLAN ───
class MaintenancePlanCreate(BaseModel):
    name: str
    name_ar: Optional[str]
    description: Optional[str]
    asset_id: int
    project_id: int
    frequency: MaintenanceFrequency
    custom_days: Optional[int]
    estimated_duration_hours: float = 1.0
    estimated_cost: float = 0.0
    required_skills: List[str] = []
    required_tools: List[str] = []
    checklist_items: List[Dict] = []
    safety_precautions: Optional[str]
    instructions: Optional[str]
    instructions_ar: Optional[str]
    start_date: Optional[date]
    notification_days_before: int = 7
    standard_reference: Optional[str]

class MaintenancePlanResponse(BaseModel):
    id: int
    plan_number: Optional[str]
    name: str
    name_ar: Optional[str]
    asset_id: int
    project_id: int
    frequency: MaintenanceFrequency
    estimated_duration_hours: float
    estimated_cost: float
    is_active: bool
    start_date: Optional[date]
    next_due_date: Optional[date]
    last_executed_date: Optional[date]
    standard_reference: Optional[str]
    checklist_items: List[Dict]
    class Config:
        from_attributes = True


# ─── WORK ORDER ───
class WorkOrderCreate(BaseModel):
    title: str
    title_ar: Optional[str]
    description: Optional[str]
    wo_type: WorkOrderType
    priority: WorkOrderPriority = WorkOrderPriority.medium
    project_id: int
    asset_id: int
    maintenance_plan_id: Optional[int]
    assigned_to_id: Optional[int]
    scheduled_date: Optional[date]
    estimated_duration_hours: Optional[float]
    estimated_cost: float = 0.0
    requires_shutdown: bool = False
    safety_measures: Optional[str]

class WorkOrderUpdate(BaseModel):
    status: Optional[WorkOrderStatus]
    assigned_to_id: Optional[int]
    scheduled_date: Optional[date]
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    actual_duration_hours: Optional[float]
    actual_cost: Optional[float]
    labor_cost: Optional[float]
    material_cost: Optional[float]
    checklist_completed: Optional[List[Dict]]
    findings: Optional[str]
    corrective_actions: Optional[str]
    completion_notes: Optional[str]
    spare_parts_used: Optional[List[Dict]]
    failure_cause: Optional[str]
    ptw_number: Optional[str]

class WorkOrderResponse(BaseModel):
    id: int
    wo_number: str
    title: str
    title_ar: Optional[str]
    wo_type: WorkOrderType
    status: WorkOrderStatus
    priority: WorkOrderPriority
    project_id: int
    asset_id: int
    assigned_to_id: Optional[int]
    scheduled_date: Optional[date]
    estimated_duration_hours: Optional[float]
    actual_duration_hours: Optional[float]
    estimated_cost: float
    actual_cost: float
    is_overdue: bool
    requires_shutdown: bool
    created_at: Optional[datetime]
    class Config:
        from_attributes = True


# ─── INVENTORY ───
class SparePartCreate(BaseModel):
    part_number: str
    name: str
    name_ar: Optional[str]
    description: Optional[str]
    category_id: Optional[int]
    asset_id: Optional[int]
    unit: str = "pcs"
    quantity_in_stock: float = 0.0
    minimum_quantity: float = 0.0
    reorder_point: float = 0.0
    unit_cost: float = 0.0
    location_in_warehouse: Optional[str]
    supplier_name: Optional[str]
    lead_time_days: int = 7
    is_critical: bool = False

class SparePartResponse(BaseModel):
    id: int
    part_number: str
    name: str
    name_ar: Optional[str]
    unit: str
    quantity_in_stock: float
    minimum_quantity: float
    reorder_point: float
    unit_cost: float
    total_value: float
    location_in_warehouse: Optional[str]
    supplier_name: Optional[str]
    is_critical: bool
    is_low_stock: Optional[bool] = False
    class Config:
        from_attributes = True


# ─── INCIDENT ───
class IncidentCreate(BaseModel):
    title: str
    description: str
    project_id: int
    severity: IncidentSeverity
    incident_date: datetime
    location: str
    immediate_actions: Optional[str]
    lost_time_hours: float = 0.0
    medical_treatment_required: bool = False

class IncidentResponse(BaseModel):
    id: int
    incident_number: Optional[str]
    title: str
    severity: IncidentSeverity
    incident_date: Optional[datetime]
    location: str
    is_closed: bool
    lost_time_hours: float
    medical_treatment_required: bool
    created_at: Optional[datetime]
    class Config:
        from_attributes = True


# ─── DASHBOARD ───
class DashboardStats(BaseModel):
    total_assets: int
    assets_operational: int
    assets_under_maintenance: int
    assets_out_of_service: int
    total_work_orders: int
    wo_pending: int
    wo_in_progress: int
    wo_overdue: int
    wo_completed_this_month: int
    wo_completion_rate: float
    total_spare_parts: int
    low_stock_items: int
    total_incidents_ytd: int
    open_ncrs: int
    mtbf_hours: float
    mttr_hours: float
    oee_pct: float
    budget_used_pct: float
    upcoming_maintenance: List[Dict]
    recent_work_orders: List[Dict]


# ─── KPI ───
class KPIResponse(BaseModel):
    period: str
    asset_availability: float
    wo_completion_rate: float
    planned_vs_actual_cost: Dict
    mtbf: float
    mttr: float
    oee: float
    incident_rate: float
    inspection_pass_rate: float
