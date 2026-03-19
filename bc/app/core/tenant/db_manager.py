"""
OMMS Multi-Tenant Database Manager
كل شركة لها قاعدة بيانات منفصلة تماماً
"""

import os
import threading
from typing import Dict, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging

logger = logging.getLogger("omms.tenant")

# ── Master DB (SaaS control plane) ─────────────────────────────
MASTER_DB_URL = os.getenv("MASTER_DATABASE_URL", "sqlite:///./omms_master.db")

master_engine = create_engine(
    MASTER_DB_URL,
    connect_args={"check_same_thread": False} if "sqlite" in MASTER_DB_URL else {},
)
MasterSession = sessionmaker(bind=master_engine, autoflush=False, autocommit=False)


def get_master_db():
    db = MasterSession()
    try:
        yield db
    finally:
        db.close()


# ── Tenant DB Registry ──────────────────────────────────────────
_tenant_engines: Dict[str, object] = {}
_tenant_sessions: Dict[str, sessionmaker] = {}
_lock = threading.Lock()


def _get_tenant_db_url(company_slug: str) -> str:
    """Build the DB URL for a tenant company"""
    base = os.getenv("TENANT_DB_BASE", "./tenant_dbs")
    os.makedirs(base, exist_ok=True)

    db_type = os.getenv("TENANT_DB_TYPE", "sqlite")

    if db_type == "sqlite":
        return f"sqlite:///{base}/{company_slug}.db"
    elif db_type == "postgresql":
        pg_host = os.getenv("PG_HOST", "localhost")
        pg_port = os.getenv("PG_PORT", "5432")
        pg_user = os.getenv("PG_USER", "omms")
        pg_pass = os.getenv("PG_PASSWORD", "omms_pass")
        # Each company gets its own PostgreSQL database
        return f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/omms_{company_slug}"
    else:
        raise ValueError(f"Unsupported DB type: {db_type}")


def get_tenant_engine(company_slug: str):
    """Get or create SQLAlchemy engine for a tenant"""
    if company_slug not in _tenant_engines:
        with _lock:
            if company_slug not in _tenant_engines:
                url = _get_tenant_db_url(company_slug)
                kwargs = {}
                if "sqlite" in url:
                    kwargs["connect_args"] = {"check_same_thread": False}
                engine = create_engine(url, **kwargs)
                _tenant_engines[company_slug] = engine
                _tenant_sessions[company_slug] = sessionmaker(
                    bind=engine, autoflush=False, autocommit=False
                )
                logger.info(f"Created engine for tenant: {company_slug}")
    return _tenant_engines[company_slug]


def get_tenant_session(company_slug: str) -> sessionmaker:
    get_tenant_engine(company_slug)
    return _tenant_sessions[company_slug]


def get_tenant_db(company_slug: str):
    """FastAPI dependency: get tenant DB session"""
    Session = get_tenant_session(company_slug)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def initialize_tenant_db(company_slug: str) -> bool:
    """Create all tables for a new tenant company"""
    from app.models.tenant.models import TenantBase
    try:
        engine = get_tenant_engine(company_slug)
        TenantBase.metadata.create_all(bind=engine)
        logger.info(f"✅ Initialized DB for tenant: {company_slug}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to init tenant DB {company_slug}: {e}")
        return False


def drop_tenant_db(company_slug: str) -> bool:
    """Drop all tables for a tenant (DANGER: data loss)"""
    from app.models.tenant.models import TenantBase
    try:
        engine = get_tenant_engine(company_slug)
        TenantBase.metadata.drop_all(bind=engine)

        # Remove from cache
        with _lock:
            _tenant_engines.pop(company_slug, None)
            _tenant_sessions.pop(company_slug, None)

        # Delete SQLite file if exists
        db_path = f"./tenant_dbs/{company_slug}.db"
        if os.path.exists(db_path):
            os.remove(db_path)

        logger.info(f"🗑️ Dropped DB for tenant: {company_slug}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to drop tenant DB {company_slug}: {e}")
        return False


def list_tenant_databases() -> list:
    """List all existing tenant databases"""
    base = os.getenv("TENANT_DB_BASE", "./tenant_dbs")
    if not os.path.exists(base):
        return []
    return [f.replace(".db", "") for f in os.listdir(base) if f.endswith(".db")]


def get_tenant_db_size(company_slug: str) -> int:
    """Get DB file size in bytes"""
    db_path = f"./tenant_dbs/{company_slug}.db"
    if os.path.exists(db_path):
        return os.path.getsize(db_path)
    return 0


def backup_tenant_db(company_slug: str, backup_dir: str = "./backups") -> Optional[str]:
    """Create a backup of tenant DB"""
    import shutil
    from datetime import datetime

    os.makedirs(backup_dir, exist_ok=True)
    src = f"./tenant_dbs/{company_slug}.db"
    if not os.path.exists(src):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{backup_dir}/{company_slug}_{timestamp}.db"
    shutil.copy2(src, dst)
    logger.info(f"📦 Backed up {company_slug} → {dst}")
    return dst
