from __future__ import annotations

from datetime import date, datetime
from typing import Optional


def fmt_date(d: Optional[date], lang: str = "de") -> str:
    if not d:
        return ""
    return d.strftime("%Y-%m-%d")


def fmt_datetime(dt: Optional[datetime], lang: str = "de") -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def fmt_money(amount: float, with_currency: bool = True, currency: str = "CHF") -> str:
    try:
        s = f"{float(amount):.2f}"
    except Exception:
        s = "0.00"
    return f"{currency} {s}" if with_currency else s
