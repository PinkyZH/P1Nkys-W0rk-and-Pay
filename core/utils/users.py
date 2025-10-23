from __future__ import annotations
from core.models import User, UserProfile

def user_label(user: User, profile: UserProfile | None) -> str:
    role = (user.role or "").upper() if user else ""
    if profile and (profile.last_name or profile.first_name):
        name = f"{profile.last_name or ''} {profile.first_name or ''}".strip()
    else:
        name = user.username if user else ""
    if role:
        return f"{name} ({role})"
    return name
