from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json, os

router = APIRouter()

PLANS_FILE = "saas_plans.json"

DEFAULT_PLANS = {
    "basic": {
        "id": "basic", "name": "Basic", "price": 1500,
        "users": "10", "projects": "3", "color": "gray",
        "featured": False, "status": "active", "subscribers": 3,
        "features": ["حتى 10 مستخدمين","3 مشاريع","أوامر العمل والصيانة","تقارير أساسية"],
        "notes": ""
    },
    "pro": {
        "id": "pro", "name": "Professional", "price": 6000,
        "users": "50", "projects": "20", "color": "blue",
        "featured": True, "status": "active", "subscribers": 7,
        "features": ["حتى 50 مستخدماً","20 مشروع","ذكاء اصطناعي وتنبؤ","تقارير متقدمة + PDF/Excel","القراءات اليومية والمستخلصات"],
        "notes": ""
    },
    "ent": {
        "id": "ent", "name": "Enterprise", "price": 19000,
        "users": "غير محدود", "projects": "غير محدودة", "color": "gold",
        "featured": False, "status": "active", "subscribers": 2,
        "features": ["مستخدمون غير محدودون","مشاريع غير محدودة","قاعدة بيانات منفصلة","تكاملات SCADA/IoT","دعم مخصص 24/7"],
        "notes": ""
    }
}

def load_plans():
    if os.path.exists(PLANS_FILE):
        try:
            with open(PLANS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_PLANS.copy()

def save_plans(plans):
    with open(PLANS_FILE, 'w', encoding='utf-8') as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

class PlanCreate(BaseModel):
    name: str
    price: float
    users: Optional[str] = "غير محدود"
    projects: Optional[str] = "غير محدود"
    color: Optional[str] = "blue"
    featured: Optional[bool] = False
    status: Optional[str] = "active"
    features: Optional[List[str]] = []
    notes: Optional[str] = ""

@router.get("/", summary="List all plans")
def list_plans():
    return load_plans()

@router.post("/", summary="Create new plan")
def create_plan(plan: PlanCreate):
    plans = load_plans()
    import time
    plan_id = "plan_" + str(int(time.time()))
    new_plan = plan.dict()
    new_plan["id"] = plan_id
    new_plan["subscribers"] = 0
    plans[plan_id] = new_plan
    save_plans(plans)
    return new_plan

@router.put("/{plan_id}", summary="Update plan")
def update_plan(plan_id: str, plan: PlanCreate):
    plans = load_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    updated = plan.dict()
    updated["id"] = plan_id
    updated["subscribers"] = plans[plan_id].get("subscribers", 0)
    plans[plan_id] = updated
    save_plans(plans)
    return updated

@router.patch("/{plan_id}/toggle", summary="Toggle plan status")
def toggle_plan(plan_id: str):
    plans = load_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    current = plans[plan_id].get("status", "active")
    plans[plan_id]["status"] = "inactive" if current == "active" else "active"
    save_plans(plans)
    return plans[plan_id]

@router.delete("/{plan_id}", summary="Delete plan")
def delete_plan(plan_id: str):
    plans = load_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    deleted = plans.pop(plan_id)
    save_plans(plans)
    return {"deleted": plan_id, "name": deleted.get("name")}
