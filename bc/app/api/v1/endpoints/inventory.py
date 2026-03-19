from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import SparePart, InventoryTransaction, User

router = APIRouter()

@router.get("/spare-parts")
def list_spare_parts(search: Optional[str]=None, low_stock_only: bool=False,
                     page: int=Query(1,ge=1), per_page: int=Query(20,ge=1,le=100),
                     db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(SparePart).filter(SparePart.is_deleted==False)
    if search: q = q.filter(SparePart.name.ilike(f"%{search}%"))
    if low_stock_only: q = q.filter(SparePart.quantity_in_stock <= SparePart.reorder_point)
    parts = q.offset((page-1)*per_page).limit(per_page).all()
    result = []
    for p in parts:
        result.append({
            "id": p.id, "part_number": p.part_number, "name": p.name, "name_ar": p.name_ar,
            "unit": p.unit, "quantity_in_stock": p.quantity_in_stock, "minimum_quantity": p.minimum_quantity,
            "reorder_point": p.reorder_point, "unit_cost": p.unit_cost,
            "total_value": round(p.quantity_in_stock * p.unit_cost, 2),
            "is_low_stock": p.quantity_in_stock <= p.reorder_point,
            "is_critical": p.is_critical, "supplier_name": p.supplier_name,
        })
    return result

@router.post("/spare-parts")
def create_spare_part(part_in: dict, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    count = db.query(SparePart).count()
    part = SparePart(**{k: v for k, v in part_in.items() if hasattr(SparePart, k)})
    if not part.part_number:
        part.part_number = f"SP-{count+1:06d}"
    db.add(part); db.commit(); db.refresh(part)
    return {"id": part.id, "part_number": part.part_number}

@router.post("/spare-parts/{part_id}/transaction")
def add_transaction(part_id: int, qty: float, tx_type: str, notes: str="",
                    db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    part = db.query(SparePart).filter(SparePart.id==part_id).first()
    if not part: raise HTTPException(404, "Part not found")
    before = part.quantity_in_stock
    if tx_type == "in": part.quantity_in_stock += qty
    elif tx_type == "out":
        if part.quantity_in_stock < qty: raise HTTPException(400, "Insufficient stock")
        part.quantity_in_stock -= qty
    tx = InventoryTransaction(spare_part_id=part_id, transaction_type=tx_type,
                              quantity=qty, quantity_before=before,
                              quantity_after=part.quantity_in_stock,
                              unit_cost=part.unit_cost, total_cost=qty*part.unit_cost,
                              notes=notes, performed_by_id=current_user.id)
    db.add(tx); db.commit()
    return {"new_quantity": part.quantity_in_stock, "is_low_stock": part.quantity_in_stock <= part.reorder_point}

@router.get("/alerts")
def get_inventory_alerts(db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    low = db.query(SparePart).filter(SparePart.quantity_in_stock <= SparePart.reorder_point,
                                     SparePart.is_deleted==False).all()
    return {"low_stock_count": len(low),
            "items": [{"id": p.id, "name": p.name, "qty": p.quantity_in_stock,
                       "reorder_point": p.reorder_point, "is_critical": p.is_critical} for p in low]}
