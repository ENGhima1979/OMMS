from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import BudgetPlan, CostTransaction, User

router = APIRouter()

@router.get("/plans")
def list_budget_plans(project_id: Optional[int]=None, year: Optional[int]=None,
                      db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(BudgetPlan).filter(BudgetPlan.is_deleted==False)
    if project_id: q = q.filter(BudgetPlan.project_id==project_id)
    if year: q = q.filter(BudgetPlan.year==year)
    plans = q.all()
    return [{"id": p.id, "project_id": p.project_id, "year": p.year,
             "total_budget": p.total_budget, "is_approved": p.is_approved} for p in plans]

@router.post("/plans")
def create_budget_plan(plan_in: dict, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    plan = BudgetPlan(**{k: v for k, v in plan_in.items() if hasattr(BudgetPlan, k)})
    db.add(plan); db.commit(); db.refresh(plan)
    return {"id": plan.id}

@router.post("/transactions")
def add_cost(tx_in: dict, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    tx = CostTransaction(**{k: v for k, v in tx_in.items() if hasattr(CostTransaction, k)},
                         recorded_by_id=current_user.id)
    db.add(tx); db.commit(); db.refresh(tx)
    return {"id": tx.id}

@router.get("/summary")
def budget_summary(project_id: int, year: Optional[int]=None,
                   db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    y = year or date.today().year
    plan = db.query(BudgetPlan).filter(BudgetPlan.project_id==project_id, BudgetPlan.year==y).first()
    actual = db.query(func.sum(CostTransaction.amount)).filter(
        CostTransaction.project_id==project_id,
        func.extract('year', CostTransaction.transaction_date)==y
    ).scalar() or 0
    total_budget = plan.total_budget if plan else 0
    return {"year": y, "total_budget": total_budget, "actual_cost": float(actual),
            "variance": total_budget - float(actual),
            "used_pct": round(float(actual)/total_budget*100 if total_budget>0 else 0, 1)}
