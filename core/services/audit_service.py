from __future__ import annotations

import json
from typing import Optional, Any

from sqlalchemy.orm import Session

from ..models import AuditLog


def _to_json(data: Any) -> str | None:
    try:
        return json.dumps(data, ensure_ascii=False, default=str) if data is not None else None
    except Exception:
        return None


def log_action(session: Session, user_id: Optional[int], action: str,
               entity: str, entity_id: Optional[str] = None,
               before: Any = None, after: Any = None, ip_addr: Optional[str] = None) -> None:
    al = AuditLog(
        user_id=user_id, action=action.upper(), entity=entity, entity_id=str(entity_id) if entity_id else None,
        before_json=_to_json(before), after_json=_to_json(after), ip_addr=ip_addr
    )
    session.add(al)
    session.commit()
