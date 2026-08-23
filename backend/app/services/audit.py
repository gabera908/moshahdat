"""Audit logging service."""
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog


def log_action(
    db: Session,
    *,
    user_id: int | None,
    action: AuditAction,
    entity_type: str,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Persist an audit record. Never raises into the request path."""
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action.value,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
        )
        db.flush()
    except Exception:  # noqa: BLE001 - audit must not break the operation
        import logging

        logging.getLogger(__name__).exception("audit log failed")
