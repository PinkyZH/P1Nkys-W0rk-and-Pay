
from __future__ import annotations
import os, hashlib, hmac
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import User, UserProfile
from ..db import Base
from config import DEFAULT_ADMIN, DEFAULT_WAGE_PRESETS

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
        profile = UserProfile(user_id=user.id, locale=DEFAULT_ADMIN.get("locale","de"),
                              hourly_brutto=DEFAULT_WAGE_PRESETS.get("hourly_brutto"),
                              vac_pct=DEFAULT_WAGE_PRESETS.get("vac_pct"),
                              holiday_pct=DEFAULT_WAGE_PRESETS.get("holiday_pct"),
                              thirteenth_pct=DEFAULT_WAGE_PRESETS.get("thirteenth_pct"),
                              expenses_per_hour=DEFAULT_WAGE_PRESETS.get("expenses_per_hour"),
                              ahv_pct=DEFAULT_WAGE_PRESETS.get("ahv_pct"),
                              nbu_pct=DEFAULT_WAGE_PRESETS.get("nbu_pct"),
                              ktg_pct=DEFAULT_WAGE_PRESETS.get("ktg_pct"),
                              bvg_pct=0.0,
                              lgav_fixed_monthly=DEFAULT_WAGE_PRESETS.get("lgav_fixed_monthly"),
                              weekly_hours=DEFAULT_WAGE_PRESETS.get("weekly_hours"))
        session.add(profile)
        session.commit()

def authenticate(session: Session, username: str, password: str) -> Optional[User]:
    user = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user: return None
    if not user.is_active: return None
    if not verify_password(password, user.password_hash): return None
    from sqlalchemy import func
    user.last_login_at = func.now()
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
