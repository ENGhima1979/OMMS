from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, projects, assets, maintenance_plans,
    work_orders, inventory, contracts, hse, quality,
    budget, dashboard, reports, notifications
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["🔐 Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["👥 Users"])
api_router.include_router(projects.router, prefix="/projects", tags=["🏗️ Projects"])
api_router.include_router(assets.router, prefix="/assets", tags=["⚙️ Assets"])
api_router.include_router(maintenance_plans.router, prefix="/maintenance-plans", tags=["📅 Maintenance Plans"])
api_router.include_router(work_orders.router, prefix="/work-orders", tags=["📋 Work Orders"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["📦 Inventory"])
api_router.include_router(contracts.router, prefix="/contracts", tags=["📄 Contracts"])
api_router.include_router(hse.router, prefix="/hse", tags=["⚠️ HSE Safety"])
api_router.include_router(quality.router, prefix="/quality", tags=["✅ Quality Control"])
api_router.include_router(budget.router, prefix="/budget", tags=["💰 Budget & Costs"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["📊 Dashboard"])
api_router.include_router(reports.router, prefix="/reports", tags=["📈 Reports"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["🔔 Notifications"])

from app.api.v1.endpoints import ai_analytics
api_router.include_router(ai_analytics.router, prefix="/ai", tags=["🤖 AI & Predictive Analytics"])

from app.api.v1.endpoints import workforce
api_router.include_router(workforce.router, prefix="/workforce", tags=["👷 Workforce"])

from app.api.v1.endpoints import saas_plans
api_router.include_router(saas_plans.router, prefix="/saas/plans", tags=["🌐 SaaS Plans"])
