from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Notification, User

router = APIRouter()

@router.get("/")
def get_notifications(unread_only: bool=False, limit: int=20,
                      db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    q = db.query(Notification).filter(Notification.user_id==current_user.id,
                                      Notification.is_deleted==False)
    if unread_only: q = q.filter(Notification.is_read==False)
    notifications = q.order_by(Notification.created_at.desc()).limit(limit).all()
    return [{"id": n.id, "title": n.title, "title_ar": n.title_ar,
             "message": n.message, "notification_type": n.notification_type,
             "is_read": n.is_read, "created_at": n.created_at} for n in notifications]

@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, db: Session=Depends(get_db),
              current_user: User=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id==notification_id,
                                      Notification.user_id==current_user.id).first()
    if n:
        n.is_read = True; db.commit()
    return {"message": "Marked as read"}

@router.patch("/mark-all-read")
def mark_all_read(db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id==current_user.id,
                                  Notification.is_read==False).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}

@router.get("/unread-count")
def unread_count(db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    count = db.query(Notification).filter(Notification.user_id==current_user.id,
                                          Notification.is_read==False).count()
    return {"unread_count": count}
