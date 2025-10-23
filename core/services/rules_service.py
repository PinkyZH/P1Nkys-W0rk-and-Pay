# workpay/core/services/rules_service.py
from __future__ import annotations
from datetime import date, datetime, time, timedelta
from typing import Tuple, Dict
from pathlib import Path
import json

from sqlalchemy.orm import Session
from config import SURCHARGE_RULES, ENABLE_SURCHARGES, HOLIDAYS_STATIC

OVERRIDE_FILE = Path(__file__).resolve().parents[2] / "data" / "state" / "surcharges.json"

def current_rules() -> Dict:
    """Lädt Override aus JSON, fällt sonst auf config.SURCHARGE_RULES zurück."""
    try:
        if OVERRIDE_FILE.exists():
            data = json.loads(OVERRIDE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                return data
    except Exception:
        pass
    return SURCHARGE_RULES

def save_rules(rules: Dict, enabled: bool) -> None:
    OVERRIDE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"enabled": bool(enabled), "rules": rules}
    OVERRIDE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def is_enabled() -> bool:
    try:
        if OVERRIDE_FILE.exists():
            data = json.loads(OVERRIDE_FILE.read_text(encoding="utf-8"))
            return bool(data.get("enabled", True))
    except Exception:
        pass
    return bool(ENABLE_SURCHARGES)

# --- Helper datums-/zeitlogik (wie zuvor) ---
def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(hour=int(h), minute=int(m))

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def is_holiday(d: date, session: Session | None = None) -> bool:
    # später: DB-Query – hier statisch aus config
    return d.isoformat() in HOLIDAYS_STATIC

def _overlap_minutes(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> int:
    start = max(a0, b0); end = min(a1, b1)
    return 0 if end <= start else int((end - start).total_seconds() // 60)

def calc_surcharges_for_entry(d: date, start_t: time | None, end_t: time | None, break_minutes: int | None) -> dict:
    res = {"NIGHT": 0, "WEEKEND": 0, "HOLIDAY": 0, "WORK_MIN": 0}
    if not is_enabled(): return res
    if not start_t or not end_t: return res

    dt0 = datetime.combine(d, start_t); dt1 = datetime.combine(d, end_t)
    if dt1 <= dt0: dt1 += timedelta(days=1)
    total_min = int((dt1 - dt0).total_seconds() // 60) - int(break_minutes or 0)
    if total_min < 0: total_min = 0
    res["WORK_MIN"] = total_min

    rules = current_rules().copy()

    # WEEKEND / HOLIDAY voll
    if rules.get("WEEKEND", {}).get("enabled") and is_weekend(d):
        res["WEEKEND"] = total_min
    if rules.get("HOLIDAY", {}).get("enabled") and is_holiday(d, None):
        res["HOLIDAY"] = total_min

    # NIGHT anteilig
    if rules.get("NIGHT", {}).get("enabled"):
        night_from = _parse_hhmm(rules["NIGHT"]["from_time"])
        night_to   = _parse_hhmm(rules["NIGHT"]["to_time"])
        n0 = datetime.combine(d, night_from)
        n1 = datetime.combine(d, time(23,59,59)) + timedelta(seconds=1)
        n2 = datetime.combine(d, time.min)
        n3 = datetime.combine(d, night_to)
        next_day = d + timedelta(days=1)
        n2_next = datetime.combine(next_day, time.min)
        n3_next = datetime.combine(next_day, night_to)
        night_min = 0
        night_min += _overlap_minutes(dt0, dt1, n0, n1)
        night_min += _overlap_minutes(dt0, dt1, n2, n3) + _overlap_minutes(dt0, dt1, n2_next, n3_next)
        if night_min > total_min: night_min = total_min
        res["NIGHT"] = night_min
    return res

def surcharge_amounts_from_minutes(minutes_map: dict, gross_per_hour: float, net_per_hour: float) -> Tuple[float,float]:
    rules_data = current_rules()
    gross = net = 0.0
    for key in ("NIGHT","WEEKEND","HOLIDAY"):
        rule = rules_data.get(key, {})
        if not rule.get("enabled"): continue
        pct = float(rule.get("percent", 0.0))/100.0
        hours = int(minutes_map.get(key, 0)) / 60.0
        gross += hours * gross_per_hour * pct
        net   += hours * net_per_hour   * pct
    return (gross, net)
