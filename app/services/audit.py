from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=json.dumps(details, ensure_ascii=False) if details else None,
            ip_address=ip_address,
        )
    )
