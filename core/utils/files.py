from __future__ import annotations

import os
import shutil

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "avatars")
os.makedirs(DATA_DIR, exist_ok=True)


def _avatar_path(user_id: int) -> str:
    return os.path.join(DATA_DIR, f"user_{user_id}.png")


def save_avatar_image(user_id: int, src_path: str) -> str:
    dst = _avatar_path(user_id)
    try:
        shutil.copyfile(src_path, dst)
        return dst
    except Exception:
        return ""


def remove_avatar_image(user_id: int) -> None:
    p = _avatar_path(user_id)
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass
