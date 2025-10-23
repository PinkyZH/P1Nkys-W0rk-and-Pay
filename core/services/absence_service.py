from __future__ import annotations
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from ..models import AbsenceRequest, WorkEntry

ABS_TYPES = {"VACATION","SICK","HOLIDAY","OFF","APPOINTMENT","HOSPITAL"}

def submit_absence(session: Session, user_id: int, typ: str, dt_from, dt_to, reason: str = "", custom_label: str | None = None) -> AbsenceRequest:
    typ = (typ or "").upper()
    if typ not in ABS_TYPES and not typ.startswith("CUSTOM:"):
        raise ValueError("Unknown absence type")
    a = AbsenceRequest(user_id=user_id, type=typ, custom_label=custom_label, date_from=dt_from, date_to=dt_to, reason=reason, status="PENDING")
    session.add(a); session.commit()
    return a

def decide_absence(session: Session, request_id: int, approve: bool, decided_by: int, note: str | None = None) -> AbsenceRequest:
    a = session.get(AbsenceRequest, request_id)
    if not a:
        raise ValueError("request not found")
    a.status = "APPROVED" if approve else "DENIED"
    from datetime import datetime as _dt
    a.decided_by = decided_by
    a.decided_at = _dt.utcnow()
    if note and not approve:
        a.reason = (a.reason or "") + f" | Admin-Note: {note}"

    # bei Genehmigung: automatische WorkEntries (Abwesenheiten = Typ ≠ WORK, zählt nicht in Lohn)
    if approve:
        cur = a.date_from
        while cur <= a.date_to:
            e = session.execute(select(WorkEntry).where(and_(WorkEntry.user_id==a.user_id, WorkEntry.date==cur))).scalars().first()
            if not e:
                e = WorkEntry(user_id=a.user_id, date=cur, entry_type=a.type, note=a.custom_label or a.reason or a.type)
                session.add(e)
            cur += timedelta(days=1)
    session.commit()
    return a

def list_requests(session: Session, status: str | None = None) -> list[AbsenceRequest]:
    stmt = select(AbsenceRequest).order_by(AbsenceRequest.created_at.desc())
    if status:
        stmt = stmt.where(AbsenceRequest.status == status)
    return session.execute(stmt).scalars().all()
