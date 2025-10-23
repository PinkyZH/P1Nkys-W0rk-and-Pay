# workpay/core/services/notification_service.py
from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from ..models import Notification

def create_notification(session: Session, user_id: int, title: str, body: str) -> Notification:
    n = Notification(user_id=user_id, title=title.strip(), body=body.strip())
    session.add(n); session.commit(); return n

def list_unread(session: Session, user_id: int) -> List[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id, Notification.is_read == False).order_by(Notification.created_at.desc())
    return session.execute(stmt).scalars().all()

def mark_all_read(session: Session, user_id: int) -> None:
    session.execute(update(Notification).where(Notification.user_id == user_id, Notification.is_read == False).values(is_read=True))
    session.commit()
