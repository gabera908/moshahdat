"""Audit log browsing (admin only)."""
from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession, Pagination, paginate_response
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
def list_audit_logs(
    db: DbSession,
    pagination: Pagination,
    _admin: AdminUser,
    action: str | None = Query(default=None, max_length=50),
    entity_type: str | None = Query(default=None, max_length=50),
    user_id: int | None = None,
) -> dict:
    """Filterable, paginated audit trail."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action.lower())
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    rows = (
        query.order_by(AuditLog.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )

    user_ids = {r.user_id for r in rows if r.user_id}
    usernames: dict[int, str] = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            usernames[u.id] = u.username

    items = []
    for r in rows:
        item = {
            "id": r.id,
            "user_id": r.user_id,
            "username": usernames.get(r.user_id),
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        items.append(item)

    return {"success": True, "message": "", "data": paginate_response(items, total, pagination)}
