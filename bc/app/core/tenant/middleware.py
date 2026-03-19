"""
OMMS Tenant Middleware
يستخرج معرف الشركة من JWT ويوجه الطلب لقاعدة البيانات الصحيحة
"""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.tenant.db_manager import get_tenant_db, get_master_db
from app.core.security import decode_token
import logging

logger = logging.getLogger("omms.tenant.middleware")
security = HTTPBearer(auto_error=False)


class TenantContext:
    """Holds the current request's tenant context"""
    def __init__(self, company_slug: str, company_id: int, user_id: int,
                 user_role: str, is_super_admin: bool = False):
        self.company_slug = company_slug
        self.company_id = company_id
        self.user_id = user_id
        self.user_role = user_role
        self.is_super_admin = is_super_admin


def get_current_tenant(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TenantContext:
    """Extract tenant context from JWT token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    is_super_admin = payload.get("role") == "super_admin"
    company_slug = payload.get("company_slug", "")

    if not is_super_admin and not company_slug:
        raise HTTPException(status_code=401, detail="No company associated with token")

    return TenantContext(
        company_slug=company_slug,
        company_id=payload.get("company_id", 0),
        user_id=payload.get("sub", 0),
        user_role=payload.get("role", "viewer"),
        is_super_admin=is_super_admin,
    )


def require_super_admin(ctx: TenantContext = Depends(get_current_tenant)) -> TenantContext:
    if not ctx.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return ctx


def get_tenant_session_dep(ctx: TenantContext = Depends(get_current_tenant)):
    """FastAPI dependency: returns the right DB session for current tenant"""
    if ctx.is_super_admin:
        # Super admin can work on master DB
        from app.core.tenant.db_manager import MasterSession
        db = MasterSession()
        try:
            yield db
        finally:
            db.close()
    else:
        from app.core.tenant.db_manager import get_tenant_session
        Session = get_tenant_session(ctx.company_slug)
        db = Session()
        try:
            yield db
        finally:
            db.close()


def get_company_db(company_slug: str):
    """Get a DB session for a specific company slug (used in admin endpoints)"""
    from app.core.tenant.db_manager import get_tenant_session
    Session = get_tenant_session(company_slug)
    db = Session()
    try:
        yield db
    finally:
        db.close()
