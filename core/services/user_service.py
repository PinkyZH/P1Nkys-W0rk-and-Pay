from __future__ import annotations

from typing import Optional, Iterable, Tuple

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from config import DEFAULT_WAGE_PRESETS as _W
from ..models import User, UserProfile
from ..utils.files import save_avatar_image, remove_avatar_image
from ..utils.validators import validate_email, validate_phone, validate_postcode, validate_iban


def get_user(session: Session, user_id: int) -> Optional[User]:
    return session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def get_profile(session: Session, user_id: int) -> Optional[UserProfile]:
    return session.execute(select(UserProfile).where(UserProfile.user_id == user_id)).scalar_one_or_none()


def list_users(session: Session, query: Optional[str] = None) -> Iterable[Tuple[User, UserProfile]]:
    stmt = select(User, UserProfile).join(UserProfile, UserProfile.user_id == User.id, isouter=True)
    if query:
        q = f"%{query}%"
        stmt = stmt.where(or_(User.username.like(q),
                              UserProfile.first_name.like(q),
                              UserProfile.last_name.like(q),
                              UserProfile.email.like(q)))
    stmt = stmt.order_by(User.id.asc())
    return session.execute(stmt).all()


def set_active(session: Session, user_id: int, active: bool) -> None:
    u = get_user(session, user_id)
    if not u: return
    u.is_active = bool(active)
    session.commit()


def update_user_and_profile(session: Session, user_id: int, **kwargs) -> None:
    u = get_user(session, user_id)
    if not u: raise ValueError("user not found")
    p = get_profile(session, user_id)
    if p is None:
        p = UserProfile(user_id=user_id)
        session.add(p);
        session.flush()

    # IBAN check
    iban = kwargs.get("iban")
    if iban and not validate_iban(iban):
        raise ValueError("invalid_iban")

    # email/phone/postcode check (soft)
    if not validate_email(kwargs.get("email")): raise ValueError("invalid_email")
    if not validate_phone(kwargs.get("phone")): raise ValueError("invalid_phone")
    if not validate_postcode(kwargs.get("postcode")): raise ValueError("invalid_postcode")

    # Avatar
    avatar_file = kwargs.pop("avatar_file", None)
    if avatar_file == "__REMOVE__":
        remove_avatar_image(user_id)
        p.avatar_path = None
    elif avatar_file:
        newp = save_avatar_image(user_id, avatar_file)
        if newp: p.avatar_path = newp

    # assign remaining simple fields (PERSON + ADMIN + BANK)
    simple_keys = [
        # Person
        "gender", "first_name", "last_name", "birthday", "civil_status", "permit_status", "locale",
        "region_code", "address", "postcode", "city", "email", "phone",
        # Admin / employment
        "employee_id", "employee_code", "employer", "employment_start",
        # Bank
        "bank_name", "bank_address", "bank_zip", "bank_city", "bank_country", "account_number", "iban",
    ]
    for k in simple_keys:
        if k in kwargs:
            setattr(p, k, kwargs[k])

    session.commit()


def delete_user(session: Session, user_id: int):
    u = get_user(session, user_id)
    if not u: return False, "not_found"
    # Prevent deleting last admin
    if (u.role or "").upper() == "ADMIN":
        cnt = session.query(User).filter(User.role == "ADMIN").count()
        if cnt <= 1:
            return False, "cannot_delete_last_admin"
    prof = get_profile(session, user_id)
    if prof and prof.avatar_path:
        try:
            remove_avatar_image(user_id)
        except Exception:
            pass
    if prof: session.delete(prof)
    session.delete(u)
    session.commit()
    return True, "deleted"


def ensure_wage_defaults(session: Session) -> None:
    # Non-destructive: if any wage field is None, fill from presets
    profiles = session.query(UserProfile).all()
    fields = [
        ("hourly_brutto", _W.get("hourly_brutto", 0.0)),
        ("vac_pct", _W.get("vac_pct", 0.0)),
        ("holiday_pct", _W.get("holiday_pct", 0.0)),
        ("thirteenth_pct", _W.get("thirteenth_pct", 0.0)),
        ("expenses_per_hour", _W.get("expenses_per_hour", 0.0)),
        ("ahv_pct", _W.get("ahv_pct", 0.0)),
        ("nbu_pct", _W.get("nbu_pct", 0.0)),
        ("ktg_pct", _W.get("ktg_pct", 0.0)),
        ("bvg_pct", 0.0),
        ("lgav_fixed_monthly", _W.get("lgav_fixed_monthly", 0.0)),
        ("weekly_hours", _W.get("weekly_hours", 41.0)),
    ]
    changed = False
    for p in profiles:
        for name, default in fields:
            if not hasattr(p, name):
                # Legacy alias: hourly_rate -> hourly_brutto
                if name == "hourly_brutto" and hasattr(p, "hourly_rate"):
                    if getattr(p, "hourly_rate") is None:
                        setattr(p, "hourly_rate", default);
                        changed = True
                continue
            if getattr(p, name) is None:
                setattr(p, name, default);
                changed = True
    if changed: session.commit()
