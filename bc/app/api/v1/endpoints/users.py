from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash
from app.models.models import User
from app.schemas.schemas import UserCreate, UserUpdate, UserResponse

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
def list_users(project_id: Optional[int]=None, search: Optional[str]=None,
               page: int=Query(1,ge=1), per_page: int=Query(20,ge=1,le=100),
               db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(User).filter(User.is_deleted==False)
    if project_id: q = q.filter(User.project_id==project_id)
    if search: q = q.filter(User.full_name.ilike(f"%{search}%"))
    return q.offset((page-1)*per_page).limit(per_page).all()

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    user = db.query(User).filter(User.id==user_id).first()
    if not user: raise HTTPException(404, "User not found")
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session=Depends(get_db),
                current_user: User=Depends(get_current_user)):
    user = db.query(User).filter(User.id==user_id).first()
    if not user: raise HTTPException(404, "User not found")
    for f, v in user_in.dict(exclude_unset=True).items():
        setattr(user, f, v)
    db.commit(); db.refresh(user)
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    user = db.query(User).filter(User.id==user_id).first()
    if not user: raise HTTPException(404, "User not found")
    user.is_deleted = True; db.commit()
    return {"message": "User deleted"}
