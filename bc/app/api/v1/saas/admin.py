"""
OMMS SaaS Admin API
إدارة الشركات والاشتراكات — للـ Super Admin فقط
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, timedelta
import re, secrets, string

from app.core.tenant.db_manager import get_master_db, initialize_tenant_db, drop_tenant_db, get_tenant_db_size, backup_tenant_db, list_tenant_databases
from app.core.security import get_password_hash
from app.models.master_models import Company, Subscription, PricingPlan, Invoice, SuperAdminUser, SystemAuditLog

router = APIRouter()


def _slug_from_name(name: str) -> str:
    """Convert company name to URL-safe slug"""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[\s_-]+', '_', slug)
    slug = slug.strip('_')[:50]
    return slug or f"company_{secrets.token_hex(4)}"


def _gen_password(length=12) -> str:
    chars = string.ascii_letters + string.digits + "!@#"
    return ''.join(secrets.choice(chars) for _ in range(length))


# ── PRICING PLANS ────────────────────────────────────────────
@router.get("/plans")
def list_plans(db: Session = Depends(get_master_db)):
    return db.query(PricingPlan).filter(PricingPlan.is_active == True).order_by(PricingPlan.sort_order).all()


@router.post("/plans")
def create_plan(
    name: str, name_ar: str,
    price_monthly: float, max_users: int = 10,
    max_projects: int = 3, max_assets: int = 100,
    features: List[str] = Body(default=[]),
    db: Session = Depends(get_master_db),
):
    plan = PricingPlan(
        name=name, name_ar=name_ar,
        price_monthly=price_monthly,
        price_annual=price_monthly * 10,  # 2 months free
        max_users=max_users,
        max_projects=max_projects,
        max_assets=max_assets,
        features=features,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/plans/{plan_id}")
def update_plan(plan_id: int, data: dict = Body(...), db: Session = Depends(get_master_db)):
    plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    for k, v in data.items():
        if hasattr(plan, k):
            setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan


# ── COMPANIES ────────────────────────────────────────────────
@router.get("/companies")
def list_companies(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_master_db),
):
    q = db.query(Company)
    if search:
        q = q.filter(
            Company.name_ar.ilike(f"%{search}%") |
            Company.name_en.ilike(f"%{search}%")
        )
    if is_active is not None:
        q = q.filter(Company.is_active == is_active)
    companies = q.order_by(Company.created_at.desc()).all()

    result = []
    for c in companies:
        sub = db.query(Subscription).filter(
            Subscription.company_id == c.id
        ).order_by(Subscription.created_at.desc()).first()

        plan = None
        if sub:
            plan = db.query(PricingPlan).filter(PricingPlan.id == sub.plan_id).first()

        result.append({
            "id": c.id,
            "slug": c.slug,
            "name_ar": c.name_ar,
            "name_en": c.name_en,
            "industry_type": c.industry_type,
            "city": c.city,
            "region": c.region,
            "is_active": c.is_active,
            "db_initialized": c.db_initialized,
            "db_size_bytes": get_tenant_db_size(c.slug),
            "created_at": c.created_at,
            "subscription": {
                "id": sub.id if sub else None,
                "status": sub.status if sub else None,
                "plan_name": plan.name if plan else None,
                "plan_name_ar": plan.name_ar if plan else None,
                "end_date": sub.end_date if sub else None,
                "current_users": sub.current_users if sub else 0,
            } if sub else None,
        })
    return result


@router.post("/companies")
def create_company(
    name_ar: str,
    name_en: str = "",
    industry_type: str = "dam",
    city: str = "",
    region: str = "",
    phone: str = "",
    email: str = "",
    commercial_registration: str = "",
    plan_id: int = 1,
    admin_name: str = "",
    admin_email: str = "",
    billing_cycle: str = "monthly",
    db: Session = Depends(get_master_db),
):
    slug = _slug_from_name(name_en or name_ar)
    # Ensure unique slug
    base_slug = slug
    counter = 1
    while db.query(Company).filter(Company.slug == slug).first():
        slug = f"{base_slug}_{counter}"
        counter += 1

    # Create company record
    company = Company(
        slug=slug,
        name_ar=name_ar,
        name_en=name_en,
        industry_type=industry_type,
        city=city,
        region=region,
        phone=phone,
        email=email,
        commercial_registration=commercial_registration,
    )
    db.add(company)
    db.flush()

    # Create subscription
    plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Pricing plan not found")

    today = date.today()
    sub = Subscription(
        company_id=company.id,
        plan_id=plan_id,
        status="trial",
        start_date=today,
        end_date=today + timedelta(days=30),  # 30-day trial
        trial_end_date=today + timedelta(days=30),
        billing_cycle=billing_cycle,
        amount=plan.price_monthly,
    )
    db.add(sub)
    db.flush()

    # Create admin user in master DB
    temp_password = _gen_password()
    if admin_email:
        admin = SuperAdminUser(
            company_id=company.id,
            username=admin_email.split("@")[0],
            email=admin_email,
            full_name=admin_name or name_ar,
            hashed_password=get_password_hash(temp_password),
            role="company_admin",
        )
        db.add(admin)

    # Initialize tenant database
    init_ok = initialize_tenant_db(slug)
    if init_ok:
        company.db_initialized = True

    # Audit log
    log = SystemAuditLog(
        company_id=company.id,
        action="company_created",
        entity_type="company",
        entity_id=company.id,
        details={"name": name_ar, "plan": plan.name, "slug": slug},
    )
    db.add(log)
    db.commit()
    db.refresh(company)

    return {
        "company": {"id": company.id, "slug": slug, "name_ar": name_ar},
        "subscription": {"status": "trial", "plan": plan.name, "trial_days": 30},
        "admin_credentials": {
            "email": admin_email,
            "temp_password": temp_password,
            "note": "Please change password on first login",
        } if admin_email else None,
        "db_initialized": init_ok,
    }


@router.get("/companies/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_master_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")

    subs = db.query(Subscription).filter(Subscription.company_id == company_id).all()
    invoices = db.query(Invoice).join(
        Subscription, Invoice.subscription_id == Subscription.id
    ).filter(Subscription.company_id == company_id).all()

    return {
        "company": company,
        "subscriptions": subs,
        "invoices": invoices,
        "db_size_bytes": get_tenant_db_size(company.slug),
    }


@router.put("/companies/{company_id}")
def update_company(company_id: int, data: dict = Body(...), db: Session = Depends(get_master_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")
    protected = {"id", "slug", "db_initialized", "created_at"}
    for k, v in data.items():
        if k not in protected and hasattr(company, k):
            setattr(company, k, v)
    db.commit()
    db.refresh(company)
    return company


@router.delete("/companies/{company_id}")
def delete_company(company_id: int, confirm: bool = False, db: Session = Depends(get_master_db)):
    if not confirm:
        raise HTTPException(400, "Must pass confirm=true to delete a company")
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")

    # Drop tenant DB
    drop_tenant_db(company.slug)

    # Soft delete
    company.is_active = False
    db.commit()
    return {"message": f"Company {company.slug} deactivated and DB dropped"}


# ── SUBSCRIPTIONS ────────────────────────────────────────────
@router.get("/subscriptions")
def list_subscriptions(
    status: Optional[str] = None,
    db: Session = Depends(get_master_db),
):
    q = db.query(Subscription)
    if status:
        q = q.filter(Subscription.status == status)
    return q.order_by(Subscription.created_at.desc()).all()


@router.patch("/subscriptions/{sub_id}")
def update_subscription(sub_id: int, data: dict = Body(...), db: Session = Depends(get_master_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    for k, v in data.items():
        if hasattr(sub, k):
            setattr(sub, k, v)
    db.commit()
    return sub


@router.post("/subscriptions/{sub_id}/renew")
def renew_subscription(
    sub_id: int,
    months: int = 12,
    db: Session = Depends(get_master_db),
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")

    plan = db.query(PricingPlan).filter(PricingPlan.id == sub.plan_id).first()

    from datetime import date
    today = date.today()
    new_end = (sub.end_date if sub.end_date > today else today) + timedelta(days=months * 30)

    sub.end_date = new_end
    sub.status = "active"
    sub.last_payment_date = today
    sub.next_payment_date = new_end

    # Create invoice
    amount = plan.price_monthly * months if plan else sub.amount * months
    invoice = Invoice(
        subscription_id=sub_id,
        invoice_number=f"INV-{today.year}-{sub_id:05d}",
        amount=amount,
        tax_amount=amount * 0.15,  # 15% VAT
        total_amount=amount * 1.15,
        status="paid",
        issue_date=today,
        due_date=today,
        paid_date=today,
    )
    db.add(invoice)
    db.commit()

    return {"subscription": sub, "invoice": invoice, "new_end_date": new_end}


@router.post("/subscriptions/{sub_id}/suspend")
def suspend_subscription(sub_id: int, db: Session = Depends(get_master_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(404)
    sub.status = "suspended"
    db.commit()
    return {"status": "suspended"}


# ── DASHBOARD / ANALYTICS ────────────────────────────────────
@router.get("/dashboard")
def saas_dashboard(db: Session = Depends(get_master_db)):
    total_companies = db.query(Company).filter(Company.is_active == True).count()
    active_subs = db.query(Subscription).filter(Subscription.status == "active").count()
    trial_subs = db.query(Subscription).filter(Subscription.status == "trial").count()
    expired_subs = db.query(Subscription).filter(Subscription.status == "expired").count()

    # Revenue this month
    today = date.today()
    month_start = today.replace(day=1)
    revenue_this_month = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.status == "paid",
        Invoice.paid_date >= month_start,
    ).scalar() or 0

    # Revenue by plan
    plans = db.query(PricingPlan).filter(PricingPlan.is_active == True).all()
    plan_stats = []
    for plan in plans:
        count = db.query(Subscription).filter(
            Subscription.plan_id == plan.id,
            Subscription.status == "active",
        ).count()
        plan_stats.append({
            "plan": plan.name,
            "plan_ar": plan.name_ar,
            "active_companies": count,
            "monthly_revenue": plan.price_monthly * count,
        })

    # Expiring soon (next 30 days)
    expiring = db.query(Subscription).filter(
        Subscription.end_date <= today + timedelta(days=30),
        Subscription.end_date >= today,
        Subscription.status == "active",
    ).count()

    return {
        "companies": {
            "total": total_companies,
            "active_subscriptions": active_subs,
            "trial": trial_subs,
            "expired": expired_subs,
            "expiring_soon": expiring,
        },
        "revenue": {
            "this_month": round(revenue_this_month, 2),
            "by_plan": plan_stats,
        },
        "db_stats": {
            "tenant_databases": list_tenant_databases(),
            "total_dbs": len(list_tenant_databases()),
        },
    }


# ── BACKUP ───────────────────────────────────────────────────
@router.post("/companies/{company_id}/backup")
def backup_company(company_id: int, db: Session = Depends(get_master_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404)
    path = backup_tenant_db(company.slug)
    if not path:
        raise HTTPException(500, "Backup failed or no DB file found")
    return {"backup_path": path, "company": company.slug}
