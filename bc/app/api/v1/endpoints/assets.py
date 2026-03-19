from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import date
import qrcode
import io
import base64

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Asset, User, AssetStatus
from app.schemas.schemas import AssetCreate, AssetUpdate, AssetResponse

router = APIRouter()


def generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def generate_asset_code(db: Session, project_id: int) -> str:
    count = db.query(Asset).filter(Asset.project_id == project_id).count()
    return f"ASSET-{project_id:03d}-{count + 1:05d}"


@router.get("/", response_model=List[AssetResponse])
def list_assets(
    project_id: Optional[int] = None,
    status: Optional[AssetStatus] = None,
    category_id: Optional[int] = None,
    criticality: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Asset).filter(Asset.is_deleted == False)

    if project_id:
        query = query.filter(Asset.project_id == project_id)
    if status:
        query = query.filter(Asset.status == status)
    if category_id:
        query = query.filter(Asset.category_id == category_id)
    if criticality:
        query = query.filter(Asset.criticality == criticality)
    if search:
        query = query.filter(
            or_(
                Asset.name.ilike(f"%{search}%"),
                Asset.name_ar.ilike(f"%{search}%"),
                Asset.asset_code.ilike(f"%{search}%"),
                Asset.serial_number.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    assets = query.offset((page - 1) * per_page).limit(per_page).all()

    # Mark low maintenance items
    today = date.today()
    for asset in assets:
        if asset.next_maintenance_date and asset.next_maintenance_date < today:
            asset.is_overdue = True

    return assets


@router.post("/", response_model=AssetResponse, status_code=201)
def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Asset).filter(Asset.asset_code == asset_in.asset_code).first():
        raise HTTPException(status_code=400, detail="Asset code already exists")

    asset = Asset(**asset_in.dict())

    # Generate QR code
    qr_data = f"OMMS|ASSET|{asset_in.asset_code}|{asset_in.name}"
    asset.qr_code = generate_qr_code(qr_data)

    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_deleted == False).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_deleted == False).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    for field, value in asset_in.dict(exclude_unset=True).items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.is_deleted = True
    db.commit()
    return {"message": "Asset deleted successfully"}


@router.get("/{asset_id}/qr-code")
def get_qr_code(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not asset.qr_code:
        qr_data = f"OMMS|ASSET|{asset.asset_code}|{asset.name}"
        asset.qr_code = generate_qr_code(qr_data)
        db.commit()
    return {"qr_code": asset.qr_code, "asset_code": asset.asset_code}


@router.get("/{asset_id}/history")
def get_asset_history(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import WorkOrder
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    work_orders = (
        db.query(WorkOrder)
        .filter(WorkOrder.asset_id == asset_id)
        .order_by(WorkOrder.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "asset": {"id": asset.id, "name": asset.name, "code": asset.asset_code},
        "total_work_orders": len(work_orders),
        "total_downtime_hours": asset.total_downtime_hours,
        "running_hours": asset.running_hours,
        "work_orders": [
            {
                "id": wo.id,
                "wo_number": wo.wo_number,
                "title": wo.title,
                "wo_type": wo.wo_type,
                "status": wo.status,
                "scheduled_date": wo.scheduled_date,
                "actual_duration_hours": wo.actual_duration_hours,
                "actual_cost": wo.actual_cost,
            }
            for wo in work_orders
        ],
    }


@router.patch("/{asset_id}/update-hours")
def update_running_hours(
    asset_id: int,
    running_hours: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.running_hours = running_hours
    db.commit()
    return {"message": "Running hours updated", "running_hours": running_hours}
