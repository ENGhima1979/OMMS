from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Contract, ContractStatus, User

router = APIRouter()

@router.get("/")
def list_contracts(project_id: Optional[int]=None, status: Optional[str]=None,
                   db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(Contract).filter(Contract.is_deleted==False)
    if project_id: q = q.filter(Contract.project_id==project_id)
    if status: q = q.filter(Contract.status==status)
    contracts = q.all()
    today = date.today()
    result = []
    for c in contracts:
        days_to_expiry = (c.end_date - today).days if c.end_date else None
        result.append({"id": c.id, "contract_number": c.contract_number, "title": c.title,
                       "party_name": c.party_name, "status": c.status, "value": c.value,
                       "start_date": c.start_date, "end_date": c.end_date,
                       "days_to_expiry": days_to_expiry,
                       "expiry_alert": days_to_expiry is not None and days_to_expiry <= 30})
    return result

@router.post("/")
def create_contract(contract_in: dict, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    count = db.query(Contract).count()
    contract = Contract(**{k: v for k, v in contract_in.items() if hasattr(Contract, k)},
                        contract_number=f"CTR-{date.today().year}-{count+1:04d}")
    db.add(contract); db.commit(); db.refresh(contract)
    return {"id": contract.id, "contract_number": contract.contract_number}

@router.get("/expiring")
def get_expiring_contracts(days: int=30, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    future = date.today() + timedelta(days=days)
    contracts = db.query(Contract).filter(Contract.end_date <= future,
                                          Contract.end_date >= date.today(),
                                          Contract.status==ContractStatus.active).all()
    return [{"id": c.id, "contract_number": c.contract_number, "title": c.title,
             "end_date": c.end_date, "days_remaining": (c.end_date - date.today()).days} for c in contracts]
