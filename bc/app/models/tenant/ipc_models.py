"""
OMMS IPC System Models — نماذج نظام المستخلصات
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.tenant.models import TenantBase
import enum


class IPCFrequency(str, enum.Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    milestone = "milestone"
    on_demand = "on_demand"


class IPCStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"
    paid = "paid"
    partially_paid = "partially_paid"


class BOQItemType(str, enum.Enum):
    work = "work"
    supply = "supply"
    service = "service"
    provisional = "provisional"
    prime_cost = "prime_cost"


class ProjectIPCSettings(TenantBase):
    __tablename__ = "project_ipc_settings"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True)
    frequency = Column(SAEnum(IPCFrequency), default=IPCFrequency.monthly)
    custom_days = Column(Integer)
    first_ipc_date = Column(Date)
    cutoff_day = Column(Integer, default=25)
    submission_day = Column(Integer, default=28)
    retention_percentage = Column(Float, default=10.0)
    advance_payment_percentage = Column(Float, default=10.0)
    advance_amount = Column(Float, default=0.0)
    advance_recovered_pct = Column(Float, default=0.0)
    contract_value = Column(Float, default=0.0)
    vat_percentage = Column(Float, default=15.0)
    notify_days_before = Column(Integer, default=7)
    notify_user_ids = Column(JSON, default=[])
    requires_engineer_approval = Column(Boolean, default=True)
    requires_pm_approval = Column(Boolean, default=True)
    requires_client_approval = Column(Boolean, default=False)
    allow_excel_upload = Column(Boolean, default=True)
    template_file_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    boq_sections = relationship("BOQSection", back_populates="settings",
                                 cascade="all, delete-orphan")


class BOQSection(TenantBase):
    __tablename__ = "boq_sections"
    id = Column(Integer, primary_key=True)
    settings_id = Column(Integer, ForeignKey("project_ipc_settings.id"))
    code = Column(String(50))
    title = Column(String(300), nullable=False)
    title_ar = Column(String(300))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    settings = relationship("ProjectIPCSettings", back_populates="boq_sections")
    items = relationship("BOQItem", back_populates="section",
                          cascade="all, delete-orphan", order_by="BOQItem.sort_order")


class BOQItem(TenantBase):
    __tablename__ = "boq_items"
    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("boq_sections.id"))
    item_number = Column(String(50))
    description = Column(Text, nullable=False)
    description_ar = Column(Text)
    item_type = Column(SAEnum(BOQItemType), default=BOQItemType.work)
    unit = Column(String(50))
    quantity = Column(Float, default=0.0)
    unit_rate = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    previous_qty = Column(Float, default=0.0)
    previous_amount = Column(Float, default=0.0)
    is_provisional = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    notes = Column(Text)

    section = relationship("BOQSection", back_populates="items")
    ipc_line_items = relationship("IPCLineItem", back_populates="boq_item")


class IPC(TenantBase):
    __tablename__ = "ipcs"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    ipc_number = Column(String(50), unique=True, nullable=False)
    ipc_title = Column(String(300))
    ipc_title_ar = Column(String(300))
    period_from = Column(Date, nullable=False)
    period_to = Column(Date, nullable=False)
    cutoff_date = Column(Date)
    status = Column(SAEnum(IPCStatus), default=IPCStatus.draft)
    # Financial
    gross_this_period = Column(Float, default=0.0)
    gross_cumulative = Column(Float, default=0.0)
    retention_pct = Column(Float, default=10.0)
    retention_this = Column(Float, default=0.0)
    retention_cumulative = Column(Float, default=0.0)
    advance_recovery_this = Column(Float, default=0.0)
    advance_recovery_cumulative = Column(Float, default=0.0)
    previous_certificates = Column(Float, default=0.0)
    net_this_period = Column(Float, default=0.0)
    vat_pct = Column(Float, default=15.0)
    vat_amount = Column(Float, default=0.0)
    total_due = Column(Float, default=0.0)
    amount_paid = Column(Float, default=0.0)
    payment_date = Column(Date)
    payment_reference = Column(String(200))
    # Files
    uploaded_excel_path = Column(String(500))
    uploaded_pdf_path = Column(String(500))
    generated_pdf_path = Column(String(500))
    # Workflow
    submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True))
    engineer_approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    engineer_approved_at = Column(DateTime(timezone=True))
    pm_approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pm_approved_at = Column(DateTime(timezone=True))
    client_approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    contractor_notes = Column(Text)
    engineer_notes = Column(Text)
    is_auto_generated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    line_items = relationship("IPCLineItem", back_populates="ipc",
                               cascade="all, delete-orphan")
    notifications = relationship("IPCNotification", back_populates="ipc")


class IPCLineItem(TenantBase):
    __tablename__ = "ipc_line_items"
    id = Column(Integer, primary_key=True)
    ipc_id = Column(Integer, ForeignKey("ipcs.id"))
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"), nullable=True)
    item_number = Column(String(50))
    description = Column(Text)
    description_ar = Column(Text)
    unit = Column(String(50))
    contract_quantity = Column(Float, default=0.0)
    previous_quantity = Column(Float, default=0.0)
    this_period_quantity = Column(Float, default=0.0)
    cumulative_quantity = Column(Float, default=0.0)
    unit_rate = Column(Float, default=0.0)
    previous_amount = Column(Float, default=0.0)
    this_period_amount = Column(Float, default=0.0)
    cumulative_amount = Column(Float, default=0.0)
    completion_pct = Column(Float, default=0.0)
    notes = Column(Text)
    is_variation = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    ipc = relationship("IPC", back_populates="line_items")
    boq_item = relationship("BOQItem", back_populates="ipc_line_items")


class IPCNotification(TenantBase):
    __tablename__ = "ipc_notifications"
    id = Column(Integer, primary_key=True)
    ipc_id = Column(Integer, ForeignKey("ipcs.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    notification_type = Column(String(50))
    title = Column(String(300))
    title_ar = Column(String(300))
    message = Column(Text)
    message_ar = Column(Text)
    due_date = Column(Date)
    is_sent = Column(Boolean, default=False)
    sent_to = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ipc = relationship("IPC", back_populates="notifications")
