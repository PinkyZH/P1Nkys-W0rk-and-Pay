# workpay/core/services/wage_service.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple, Optional

from sqlalchemy.orm import Session

from config import DEFAULT_WAGE_PRESETS as _W
from config import ROUND_TO_0_05
from ..models import UserProfile

# Datei für globale (firmweite) Overrides
_OVR_PATH = Path(__file__).resolve().parents[2] / "data" / "state" / "wage_defaults.json"


def _round_0_05(v: float) -> float:
    return round(v * 20) / 20.0 if ROUND_TO_0_05 else v


def _load_global_defaults() -> Dict[str, float]:
    """Firmweite Defaults aus JSON; Fallback auf config.DEFAULT_WAGE_PRESETS."""
    try:
        if _OVR_PATH.exists():
            data = json.loads(_OVR_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                return {**_W, **{k: float(v) for k, v in data.items() if v is not None}}
    except Exception:
        pass
    return dict(_W)


def save_global_defaults(new_vals: Dict[str, float]) -> None:
    """Schreibt firmweite Defaults (ohne Stunden/Monat etc.; nur relevante Keys)."""
    _OVR_PATH.parent.mkdir(parents=True, exist_ok=True)
    # nur bekannte Keys erlauben
    allowed = {
        "hourly_brutto", "vac_pct", "holiday_pct", "thirteenth_pct", "expenses_per_hour",
        "ahv_pct", "nbu_pct", "ktg_pct", "bvg_pct", "lgav_fixed_monthly", "weekly_hours"
    }
    clean = {k: float(v) for k, v in new_vals.items() if k in allowed and v is not None}
    _OVR_PATH.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")


def _val_or_fallback(profile: Optional[UserProfile], name: str, defaults: Dict[str, float]) -> float:
    if profile is not None and getattr(profile, name) is not None:
        return float(getattr(profile, name))
    return float(defaults.get(name, 0.0))


def get_hour_rates(session: Session, user_id: int) -> tuple[float, float]:
    """Öffentliche Kurz-API: nur (Brutto/Std, Netto/Std)."""
    p = session.query(UserProfile).filter(UserProfile.user_id == user_id).one_or_none()
    dfl = _load_global_defaults()

    hb = _val_or_fallback(p, "hourly_brutto", dfl)
    vac = _val_or_fallback(p, "vac_pct", dfl)
    hol = _val_or_fallback(p, "holiday_pct", dfl)
    m13 = _val_or_fallback(p, "thirteenth_pct", dfl)
    exp = _val_or_fallback(p, "expenses_per_hour", dfl)
    ahv = _val_or_fallback(p, "ahv_pct", dfl)
    nbu = _val_or_fallback(p, "nbu_pct", dfl)
    ktg = _val_or_fallback(p, "ktg_pct", dfl)
    bvg = _val_or_fallback(p, "bvg_pct", dfl)

    gross_hr = hb * (1 + (vac + hol + m13) / 100.0) + exp
    net_hr = hb * (1 + (vac + hol + m13) / 100.0) * (1 - (ahv + nbu + ktg + bvg) / 100.0) + exp

    return (_round_0_05(gross_hr), _round_0_05(net_hr))


def get_full_breakdown(session: Session, user_id: int, hours_month: float = 174.0) -> Dict[str, float]:
    """Für Vorschau: alle Einzelwerte + Monatssummen."""
    gh, nh = get_hour_rates(session, user_id)
    return {
        "gross_per_hour": gh,
        "net_per_hour": nh,
        "gross_per_month": _round_0_05(gh * hours_month),
        "net_per_month": _round_0_05(nh * hours_month),
    }


def validate_rule_values(vals: Dict[str, float]) -> Tuple[bool, str]:
    """Basisvalidierung: Prozente 0..100, Beträge >= 0."""
    pct_keys = ["vac_pct", "holiday_pct", "thirteenth_pct", "ahv_pct", "nbu_pct", "ktg_pct", "bvg_pct"]
    amt_keys = ["hourly_brutto", "expenses_per_hour", "lgav_fixed_monthly", "weekly_hours"]
    for k in pct_keys:
        v = float(vals.get(k, 0.0))
        if v < 0 or v > 100:
            return False, f"Wert {k} muss zwischen 0 und 100 liegen."
    for k in amt_keys:
        if k in vals:
            v = float(vals.get(k, 0.0))
            if v < 0:
                return False, f"Wert {k} darf nicht negativ sein."
    return True, ""


def save_user_overrides(session: Session, user_id: int, vals: Dict[str, float]) -> None:
    """Schreibt Felder ins UserProfile (nur Keys, die vorhanden sind)."""
    ok, msg = validate_rule_values(vals)
    if not ok:
        raise ValueError(msg)
    p = session.query(UserProfile).filter(UserProfile.user_id == user_id).one_or_none()
    if p is None:
        p = UserProfile(user_id=user_id)
        session.add(p)
    for k, v in vals.items():
        if hasattr(p, k):
            setattr(p, k, float(v) if v is not None else None)
    session.commit()


def reset_user_overrides(session: Session, user_id: int) -> None:
    """Setzt die Felder auf None -> Fallback auf Global Defaults."""
    p = session.query(UserProfile).filter(UserProfile.user_id == user_id).one_or_none()
    if not p:
        return
    for k in ["hourly_brutto", "vac_pct", "holiday_pct", "thirteenth_pct", "expenses_per_hour",
              "ahv_pct", "nbu_pct", "ktg_pct", "bvg_pct", "lgav_fixed_monthly", "weekly_hours"]:
        if hasattr(p, k):
            setattr(p, k, None)
    session.commit()


def simulate_from_params(params: Dict[str, float], hours_month: float = 174.0) -> Dict[str, float]:
    """Rechnet direkt aus Parametern (GUI-Preview), ohne DB; nutzt 0.05-Rundung."""
    ok, msg = validate_rule_values(params)
    if not ok:
        raise ValueError(msg)

    hb = float(params.get("hourly_brutto", 0.0))
    vac = float(params.get("vac_pct", 0.0))
    hol = float(params.get("holiday_pct", 0.0))
    m13 = float(params.get("thirteenth_pct", 0.0))
    exp = float(params.get("expenses_per_hour", 0.0))
    ahv = float(params.get("ahv_pct", 0.0))
    nbu = float(params.get("nbu_pct", 0.0))
    ktg = float(params.get("ktg_pct", 0.0))
    bvg = float(params.get("bvg_pct", 0.0))

    gross_hr = hb * (1 + (vac + hol + m13) / 100.0) + exp
    net_hr = hb * (1 + (vac + hol + m13) / 100.0) * (1 - (ahv + nbu + ktg + bvg) / 100.0) + exp

    gh = _round_0_05(gross_hr)
    nh = _round_0_05(net_hr)
    return {
        "gross_per_hour": gh,
        "net_per_hour": nh,
        "gross_per_month": _round_0_05(gh * hours_month),
        "net_per_month": _round_0_05(nh * hours_month),
    }
