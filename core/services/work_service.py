from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from .audit_service import log_action
from ..models import WorkEntry


def _to_hours(start: Optional[time], end: Optional[time], break_minutes: Optional[int]) -> Optional[float]:
    if not start or not end:
        return None
    dt0 = datetime.combine(date.today(), start)
    dt1 = datetime.combine(date.today(), end)
    if dt1 < dt0:
        dt1 += timedelta(days=1)
    minutes = (dt1 - dt0).total_seconds() / 60.0
    minutes -= float(break_minutes or 0)
    if minutes < 0: minutes = 0
    return round(minutes / 60.0, 2)


def get_entry(session: Session, entry_id: int) -> Optional[WorkEntry]:
    return session.get(WorkEntry, entry_id)


def list_entries_by_range(session: Session, user_id: int, start_d: date, end_d: date) -> List[WorkEntry]:
    stmt = select(WorkEntry).where(
        and_(WorkEntry.user_id == user_id, WorkEntry.date >= start_d, WorkEntry.date <= end_d)).order_by(
        WorkEntry.date.asc(), WorkEntry.start_time.asc().nullsfirst())
    return list(session.execute(stmt).scalars().all())


def list_entries_by_date(session: Session, user_id: int, d: date) -> List[WorkEntry]:
    stmt = select(WorkEntry).where(and_(WorkEntry.user_id == user_id, WorkEntry.date == d)).order_by(
        WorkEntry.start_time.asc().nullsfirst())
    return list(session.execute(stmt).scalars().all())


def create_entry(session: Session, user_id: int, **kwargs) -> WorkEntry:
    e = WorkEntry(user_id=user_id)
    for k in ("date", "start_time", "end_time", "break_minutes", "hours", "entry_type", "note", "hourly_override",
              "overtime_hours", "location"):
        if k in kwargs: setattr(e, k, kwargs[k])
    if e.hours is None:
        e.hours = _to_hours(e.start_time, e.end_time, e.break_minutes)
    session.add(e);
    session.commit()

    log_action(session, user_id, "CREATE", "WorkEntry", entity_id=e.id, after={
        "date": e.date.isoformat(), "start": str(e.start_time), "end": str(e.end_time),
        "break": e.break_minutes, "hours": e.hours, "type": e.entry_type, "note": e.note
    })

    return e


def update_entry(session: Session, entry_id: int, **kwargs) -> Optional[WorkEntry]:
    e = session.get(WorkEntry, entry_id)
    if not e: return None
    for k in ("date", "start_time", "end_time", "break_minutes", "hours", "entry_type", "note", "hourly_override",
              "overtime_hours", "location"):
        if k in kwargs: setattr(e, k, kwargs[k])
    if any(k in kwargs for k in ("start_time", "end_time", "break_minutes")):
        e.hours = _to_hours(e.start_time, e.end_time, e.break_minutes) if e.start_time and e.end_time else e.hours

    before = {"date": e.date.isoformat(), "start": str(e.start_time), "end": str(e.end_time),
              "break": e.break_minutes, "hours": e.hours, "type": e.entry_type, "note": e.note}
    # ... dann Felder setzen, commit ...
    log_action(session, e.user_id, "UPDATE", "WorkEntry", entity_id=e.id, before=before, after={
        "date": e.date.isoformat(), "start": str(e.start_time), "end": str(e.end_time),
        "break": e.break_minutes, "hours": e.hours, "type": e.entry_type, "note": e.note
    })

    session.commit();
    return e


def delete_entry(session: Session, entry_id: int) -> bool:
    e = session.get(WorkEntry, entry_id)
    if not e: return False

    log_action(session, e.user_id, "DELETE", "WorkEntry", entity_id=e.id, before={
        "date": e.date.isoformat(), "start": str(e.start_time), "end": str(e.end_time),
        "break": e.break_minutes, "hours": e.hours, "type": e.entry_type, "note": e.note
    })

    session.delete(e);
    session.commit();
    return True


def totals_for_range(session: Session, user_id: int, start_d: date, end_d: date) -> Tuple[float, int]:
    stmt = select(func.coalesce(func.sum(WorkEntry.hours), 0.0), func.count(WorkEntry.id)).where(
        and_(WorkEntry.user_id == user_id, WorkEntry.date >= start_d, WorkEntry.date <= end_d))
    hours_sum, count_entries = session.execute(stmt).one()
    return (float(hours_sum or 0.0), int(count_entries or 0))


def dates_with_entries_by_month(session: Session, user_id: int, year: int, month: int) -> dict:
    from calendar import monthrange
    from datetime import date as _d
    first = _d(year, month, 1)
    last = _d(year, month, monthrange(year, month)[1])
    stmt = select(WorkEntry.date, func.count(WorkEntry.id)).where(
        and_(WorkEntry.user_id == user_id, WorkEntry.date >= first, WorkEntry.date <= last)).group_by(WorkEntry.date)
    res = {}
    for d, cnt in session.execute(stmt).all():
        res[d] = int(cnt or 0)
    return res
