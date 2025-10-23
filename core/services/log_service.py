# workpay/core/services/log_service.py
from __future__ import annotations
import json, logging, logging.handlers, os
from pathlib import Path
from typing import Any, Dict, Optional

BASE = Path(os.path.dirname(os.path.dirname(__file__))).parent
LOG_DIR = BASE / "logs"
USER_DIR = LOG_DIR / "users"
ERROR_FILE = LOG_DIR / "errors.log"

_LOGGERS: Dict[int, logging.Logger] = {}
_CONFIGURED = False

def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED: return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    USER_DIR.mkdir(parents=True, exist_ok=True)

    # Fehler-Gesamtlog
    err_logger = logging.getLogger("workpay.errors")
    err_logger.setLevel(logging.INFO)
    eh = logging.handlers.RotatingFileHandler(ERROR_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    eh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    err_logger.addHandler(eh)

    _CONFIGURED = True

def _user_logger(user_id: int) -> logging.Logger:
    setup_logging()
    if user_id in _LOGGERS:
        return _LOGGERS[user_id]
    lg = logging.getLogger(f"workpay.user.{user_id}")
    lg.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(USER_DIR / f"{user_id}.log",
                                              maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    lg.addHandler(fh)
    _LOGGERS[user_id] = lg
    return lg

def log_activity(user_id: int, action: str, meta: Optional[Dict[str, Any]] = None) -> None:
    """
    Schreibt in logs/users/<user_id>.log eine JSON-Zeile:
    {"action": "...", "meta": {...}}
    """
    try:
        lg = _user_logger(user_id)
        payload = {"action": action}
        if meta: payload["meta"] = meta
        lg.info(json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass

def log_error(msg: str, *, exc: Optional[BaseException] = None) -> None:
    setup_logging()
    logging.getLogger("workpay.errors").error(msg, exc_info=exc)

def list_user_log_files() -> Dict[int, Path]:
    setup_logging()
    out: Dict[int, Path] = {}
    for p in USER_DIR.glob("*.log"):
        try:
            uid = int(p.stem)
            out[uid] = p
        except Exception:
            continue
    return out

def read_log(path: Path, max_lines: int = 500) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-max_lines:]
        return "".join(lines)
    except Exception:
        return ""
