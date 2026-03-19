"""
OMMS - Operation & Maintenance Management System
نظام إدارة التشغيل والصيانة المتكامل
Version: 2.0.0 | Python FastAPI Backend
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("omms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 60)
    logger.info("  OMMS v2.0.0 — Operation & Maintenance Management System")
    logger.info("  نظام إدارة التشغيل والصيانة المتكامل")
    logger.info("=" * 60)

    # Create DB tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables initialized")

    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"✅ Upload directory: {settings.UPLOAD_DIR}")

    # Start scheduler
    try:
        from app.services.scheduler import start_scheduler
        start_scheduler()
        logger.info("✅ Background scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler not started: {e}")

    logger.info("🚀 OMMS is ready — Docs: http://localhost:8000/api/docs")
    yield

    # Shutdown
    try:
        from app.services.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    logger.info("🛑 OMMS shutdown complete")


app = FastAPI(
    title="OMMS — Operation & Maintenance Management System",
    description="""
## نظام إدارة التشغيل والصيانة المتكامل

**OMMS v2.0.0** is a comprehensive ERP system for managing preventive and corrective
maintenance for dams, water treatment plants, power stations, and industrial facilities.

### 📦 Modules:
| # | Module | الوحدة |
|---|--------|--------|
| 1 | Asset Management | إدارة الأصول |
| 2 | Maintenance Plans | خطط الصيانة الوقائية |
| 3 | Work Orders | أوامر العمل |
| 4 | Inventory | المخازن وقطع الغيار |
| 5 | Workforce | إدارة الكوادر |
| 6 | Contracts | إدارة العقود |
| 7 | Budget & Costs | الميزانية والتكاليف |
| 8 | HSE Safety | السلامة والمخاطر |
| 9 | Quality Control | مراقبة الجودة |
| 10 | Reports & KPIs | التقارير والمؤشرات |
| 11 | Notifications | الإشعارات |
| 12 | AI Predictive | الذكاء الاصطناعي |

### 🔐 Authentication:
Use `/api/v1/auth/login` with username and password to get a JWT token.
Include the token in the `Authorization: Bearer <token>` header.

### 👤 Default Credentials:
- **admin / admin123** — Super Admin
- **engineer / eng123** — Maintenance Engineer
- **technician / tech123** — Field Technician

> Run `python seed.py` first to populate demo data.
    """,
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "OMMS Support",
        "email": "support@omms.sa",
    },
    license_info={
        "name": "Enterprise License",
    },
)

# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(duration)
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found", "path": str(request.url.path)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routes ────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["System"])
async def root():
    return {
        "system": "OMMS — Operation & Maintenance Management System",
        "system_ar": "نظام إدارة التشغيل والصيانة المتكامل",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/api/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"])
async def health_check():
    from app.core.database import SessionLocal
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "healthy",
        "version": "2.0.0",
        "database": db_status,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }
