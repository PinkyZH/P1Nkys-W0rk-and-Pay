from __future__ import annotations

import json
import os
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(__file__))).parent
STATE_DIR = BASE / "data" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
APP_SETTINGS_FILE = STATE_DIR / "app.json"

_DEFAULTS = {"lang": "de"}


def load_app_settings() -> dict:
    if APP_SETTINGS_FILE.exists():
        try:
            return json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return dict(_DEFAULTS)
    return dict(_DEFAULTS)


def save_app_settings(cfg: dict) -> None:
    try:
        APP_SETTINGS_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_lang() -> str:
    return load_app_settings().get("lang", "de")


def set_lang(lang: str) -> None:
    cfg = load_app_settings()
    cfg["lang"] = lang
    save_app_settings(cfg)


def get_user_pref(user_id: int, key: str, default=None):
    cfg = load_app_settings()
    ucfg = cfg.setdefault("user_prefs", {})
    return ucfg.get(str(user_id), {}).get(key, default)


def set_user_pref(user_id: int, key: str, value):
    cfg = load_app_settings()
    ucfg = cfg.setdefault("user_prefs", {})
    ucfg.setdefault(str(user_id), {})[key] = value
    save_app_settings(cfg)
