from __future__ import annotations
from typing import Tuple, Dict, List
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from ..models import WorkEntry, UserProfile
from config import DEFAULT_WAGE_PRESETS as _W

def period_range(mode: str, anchor: date) -> Tuple[date, date]:
    m = mode.upper()
    if m == "DAY":
        return (anchor, anchor)
    if m == "WEEK":
        start = anchor - timedelta(days=anchor.weekday())
        return (start, start + timedelta(days=6))
    if m == "MONTH":
        start = anchor.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year+1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month+1, day=1) - timedelta(days=1)
        return (start, end)
    start = anchor.replace(month=1, day=1)
    end = anchor.replace(month=12, day=31)
    return (start, end)

def _wage_per_hour(session: Session, user_id: int) -> Tuple[float,float]:
    p = session.query(UserProfile).filter(UserProfile.user_id==user_id).one_or_none()
    def _v(n, d=0.0): return (getattr(p, n) if (p and getattr(p, n) is not None) else _W.get(n, d))
    hb=_v("hourly_brutto"); vac=_v("vac_pct"); hol=_v("holiday_pct"); m13=_v("thirteenth_pct")
    exp=_v("expenses_per_hour"); ahv=_v("ahv_pct"); nbu=_v("nbu_pct"); ktg=_v("ktg_pct"); bvg=(p.bvg_pct if p and p.bvg_pct is not None else 0.0)
    gross_hr = hb*(1+(vac+hol+m13)/100.0) + exp
    net_hr   = hb*(1+(vac+hol+m13)/100.0)*(1-(ahv+nbu+ktg+bvg)/100.0) + exp
    return (float(gross_hr), float(net_hr))

def hours_and_entries(session: Session, user_id: int, start: date, end: date) -> Tuple[float,int]:
    stmt = select(func.coalesce(func.sum(WorkEntry.hours), 0.0), func.count(WorkEntry.id))\
        .where(and_(WorkEntry.user_id==user_id, WorkEntry.date>=start, WorkEntry.date<=end))
    hours_sum, cnt = session.execute(stmt).one()
    return (float(hours_sum or 0.0), int(cnt or 0))

def earnings_for_range(session: Session, user_id: int, start: date, end: date) -> Tuple[float,float,float,int]:
    hours, entries = hours_and_entries(session, user_id, start, end)
    gross_hr, net_hr = _wage_per_hour(session, user_id)
    return (hours, gross_hr*hours, net_hr*hours, int(entries))

def breakdown_by_type(session: Session, user_id: int, start: date, end: date) -> Dict[str, Tuple[float,int]]:
    stmt = select(WorkEntry.entry_type, func.coalesce(func.sum(WorkEntry.hours),0.0), func.count(WorkEntry.id))\
        .where(and_(WorkEntry.user_id==user_id, WorkEntry.date>=start, WorkEntry.date<=end))\
        .group_by(WorkEntry.entry_type)
    out = {}
    for t, h, c in session.execute(stmt).all():
        out[(t or "WORK").upper()] = (float(h or 0.0), int(c or 0))
    return out

def daily_trend(session: Session, user_id: int, start: date, end: date) -> List[Tuple[date, float]]:
    stmt = select(WorkEntry.date, func.coalesce(func.sum(WorkEntry.hours), 0.0))\
        .where(and_(WorkEntry.user_id==user_id, WorkEntry.date>=start, WorkEntry.date<=end))\
        .group_by(WorkEntry.date).order_by(WorkEntry.date.asc())
    return [(d, float(h or 0.0)) for d, h in session.execute(stmt).all()]