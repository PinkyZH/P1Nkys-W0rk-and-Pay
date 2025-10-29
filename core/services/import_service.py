from __future__ import annotations

import csv
from datetime import datetime, time
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import WorkEntry


def parse_time(s: str | None) -> time | None:
    if not s: return None
    s = s.strip()
    fmt = "%H:%M"
    return datetime.strptime(s, fmt).time()


def import_entries_csv(session: Session, user_id: int, csv_path: Path) -> int:
    """
    CSV Spalten: date,start,end,break,type,note,location
    date=YYYY-MM-DD; break=Minuten (int)
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    added = 0
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            st = parse_time(row.get("start"))
            en = parse_time(row.get("end"))
            br = int(row.get("break") or 0)
            typ = (row.get("type") or "WORK").upper()
            note = (row.get("note") or "").strip()
            loc = (row.get("location") or "").strip()
            e = WorkEntry(user_id=user_id, date=d, start_time=st, end_time=en, break_minutes=br,
                          entry_type=typ, note=note, location=loc)
            session.add(e);
            added += 1
    session.commit()
    return added
