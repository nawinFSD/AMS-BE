from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database.connection import get_db
from app.models.domain import User, Notification, UserRole
from app.schemas.schemas import NotificationResponse
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


class NotificationCreatePayload(BaseModel):
    title: str
    message: str
    user_id: Optional[int] = None
    role: Optional[str] = None


@router.get("", response_model=List[NotificationResponse])
def get_my_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    return query.order_by(Notification.createdAt.desc()).limit(limit).all()


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False  # noqa: E712
    ).count()
    return {"count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False  # noqa: E712
    ).update({Notification.is_read: True})
    db.commit()
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notif)
    db.commit()
    return {"message": "Notification deleted"}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN.value]))
):
    if payload.user_id:
        target = db.query(User).filter(User.id == payload.user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        notif = Notification(
            user_id=target.id,
            title=payload.title,
            message=payload.message
        )
        db.add(notif)
        db.commit()
        return {"message": "Notification sent", "notification_id": notif.id}
    if payload.role:
        users = db.query(User).filter(User.role == payload.role).all()
        for u in users:
            db.add(Notification(user_id=u.id, title=payload.title, message=payload.message))
        db.commit()
        return {"message": f"Notification broadcast to {len(users)} {payload.role} user(s)"}
    raise HTTPException(status_code=400, detail="Provide either user_id or role")
