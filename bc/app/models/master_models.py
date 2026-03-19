"""
OMMS Master Database Models
قاعدة البيانات الرئيسية — تحكم SaaS (الشركات، الاشتراكات، الباقات)
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

MasterBase = declarative_base()


class SubscriptionPlan(str, enum.Enum):
    basic = "basic"
    professional = "professional"
    enterprise = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    trial = "trial"
    active = "active"
    suspended = "suspended"
    expired = "expired"
    cancelled = "cancelled"


class Company(MasterBase):
    """شركة مشتركة في النظام"""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    # Identity
    slug = Column(String(100), unique=True, index=True, nullable=False)  # used as DB name
    name_ar = Column(String(300), nullable=False)
    name_en = Column(String(300))
    logo_url = Column(String(500))
    # Business info
    commercial_registration = Column(String(100))
    vat_number = Column(String(50))
    industry_type = Column(String(100))  # dams, water, energy, oil_gas, contracting
    city = Column(String(100))
    region = Column(String(100))
    country = Column(String(50), default="SA")
    address = Column(Text)
    phone = Column(String(30))
    email = Column(String(255))
    website = Column(String(300))
    # Settings
    timezone = Column(String(50), default="Asia/Riyadh")
    language = Column(String(10), default="ar")
    currency = Column(String(10), default="SAR")
    settings = Column(JSON, default={})
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # DB
    db_initialized = Column(Boolean, default=False)
    db_size_bytes = Column(Integer, default=0)

    subscriptions = relationship("Subscription", back_populates="company")
    admin_users = relationship("SuperAdminUser", back_populates="company")


class PricingPlan(MasterBase):
    """باقات الاشتراك"""
    __tablename__ = "pricing_plans"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # basic, professional, enterprise
    name_ar = Column(String(100))
    price_monthly = Column(Float, nullable=False)
    price_annual = Column(Float)  # discounted annual price
    max_users = Column(Integer, default=10)
    max_projects = Column(Integer, default=3)
    max_assets = Column(Integer, default=100)
    features = Column(JSON, default=[])  # list of feature keys
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(MasterBase):
    """اشتراك شركة في باقة معينة"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, index=True)
    plan_id = Column(Integer, index=True)
    status = Column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.trial)
    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    trial_end_date = Column(Date)
    # Billing
    billing_cycle = Column(String(20), default="monthly")  # monthly, annual
    amount = Column(Float)
    currency = Column(String(10), default="SAR")
    payment_method = Column(String(50))
    last_payment_date = Column(Date)
    next_payment_date = Column(Date)
    # Usage
    current_users = Column(Integer, default=0)
    current_projects = Column(Integer, default=0)
    current_assets = Column(Integer, default=0)
    # Notes
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="subscriptions")
    plan = relationship("PricingPlan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")


class Invoice(MasterBase):
    """فواتير الاشتراك"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, index=True)
    invoice_number = Column(String(50), unique=True)
    amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float)
    currency = Column(String(10), default="SAR")
    status = Column(String(20), default="pending")  # pending, paid, overdue, cancelled
    issue_date = Column(Date)
    due_date = Column(Date)
    paid_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscription = relationship("Subscription", back_populates="invoices")


class SuperAdminUser(MasterBase):
    """مستخدمو Super Admin (إدارة النظام العامة)"""
    __tablename__ = "super_admin_users"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, nullable=True)  # None = global super admin
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(200))
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="super_admin")  # super_admin, support, billing
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="admin_users")


class SystemAuditLog(MasterBase):
    """سجل أحداث النظام العام"""
    __tablename__ = "system_audit_logs"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, nullable=True)
    admin_user_id = Column(Integer)
    action = Column(String(100))  # company_created, subscription_updated, etc.
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
