
from __future__ import annotations
import os, hashlib, hmac
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import User, UserProfile

from config import DEFAULT_ADMIN, DEFAULT_WAGE_PRESETS

from ..db import Base

# PBKDF2 (no external dep)
def _pbkdf2(password: str, salt: bytes, iterations: int = 200_000, dklen: int = 32) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen)

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = _pbkdf2(password, salt)
    return salt.hex() + ":" + dk.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        dk = bytes.fromhex(dk_hex)
        test = _pbkdf2(password, salt)
        return hmac.compare_digest(test, dk)
    except Exception:
        return False
def ensure_default_admin(session: Session) -> None:
    # Create admin if missing
    user = session.execute(select(User).where(User.username == DEFAULT_ADMIN["username"])).scalar_one_or_none()
    if user is None:
        user = User(
            username=DEFAULT_ADMIN["username"],
            password_hash=hash_password(DEFAULT_ADMIN["password"]),
            role="ADMIN",
            is_active=True,
            must_change_password=True,
        )
        session.add(user); session.flush()
        # nur Felder befüllen, die es im Model gibt
        allowed_profile_keys = {
            "locale",
            "hourly_brutto", "vac_pct", "holiday_pct", "thirteenth_pct",
            "expenses_per_hour",
            "ahv_pct", "nbu_pct", "ktg_pct", "bvg_pct",
            "weekly_hours",
            # falls du noch andere existierende Spalten pflegen willst, hier ergänzen:
            # "first_name", "last_name", "address", "postcode", "city", "email", "phone",
            # "employee_id", "employee_code", "employer", "employment_start",
            # "iban", "bank_name", "bank_address", "bank_zip", "bank_city", "bank_country", "account_number",
            # "ahv_number",
        }
        profile_kwargs = {}
        for k in allowed_profile_keys:
            v = DEFAULT_ADMIN.get(k)
            if v is not None:
                profile_kwargs[k] = v

        profile = UserProfile(user_id=user.id, **profile_kwargs)
        session.add(profile)
        session.commit()

def authenticate(session: Session, username: str, password: str) -> Optional[User]:
    user = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user: return None
    if not user.is_active: return None
    if not verify_password(password, user.password_hash): return None
    from sqlalchemy import func
    user.last_login = func.now()
    session.commit()
    session.commit()
    return user

def update_password(session: Session, user: User, new_password: str, force_change: bool = False) -> None:
    user.password_hash = hash_password(new_password)
    user.must_change_password = bool(force_change)
    session.commit()

def admin_reset_password(session: Session, user_id: int, new_password: str, force_change: bool = True) -> None:
    user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user: return
    update_password(session, user, new_password, force_change=force_change)
