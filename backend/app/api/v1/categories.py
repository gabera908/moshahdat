"""Categories: public reads + staff writes + hierarchy support."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import (
    DbSession,
    StaffUser,
    STAFF_ROLES,
    get_current_user_optional,
)
from app.models.category import Category
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.schemas.common import ApiResponse
from app.schemas.taxonomy import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ReorderRequest,
)
from app.services.audit import AuditAction, log_action
from app.services.slugs import unique_slug

router = APIRouter(prefix="/categories", tags=["categories"])


def _serialize(c: Category) -> CategoryOut:
    return CategoryOut.model_validate(c)


@router.get("")
def list_categories(
    db: DbSession,
    include_inactive: bool = Query(default=False),
    _user: User | None = Depends(get_current_user_optional),
) -> dict:
    """Public listing; inactive items are visible to staff only."""
    query = db.query(Category).order_by(Category.sort_order.asc(), Category.name.asc())
    is_staff = _user is not None and _user.role in STAFF_ROLES
    if not (include_inactive and is_staff):
        query = query.filter(Category.is_active.is_(True))

    cats = query.all()

    counts: dict[int | None, int] = {}
    rows = (
        db.query(Video.category_id)
        .filter(Video.status == VideoStatus.PUBLISHED, Video.deleted_at.is_(None))
        .all()
    )
    for (cid,) in rows:
        counts[cid] = counts.get(cid, 0) + 1

    data = []
    for c in cats:
        item = _serialize(c).model_dump(mode="json")
        item["videos_count"] = counts.get(c.id, 0)
        data.append(item)

    return {"success": True, "message": "", "data": {"items": data}}


def _validate_parent(db: DbSession, parent_id: int | None, self_id: int | None = None) -> None:
    """Ensure a valid, acyclic parent for the category tree."""
    if not parent_id:
        return
    if self_id is not None and parent_id == self_id:
        raise HTTPException(status_code=422, detail="لا يمكن أن يكون التصنيف أبًا لنفسه")
    seen: set[int] = set()
    current = db.get(Category, parent_id)
    while current is not None and current.parent_id:
        if current.id in seen:
            break
        seen.add(current.id)
        if self_id is not None and current.parent_id == self_id:
            raise HTTPException(status_code=422, detail="هذا الاختيار يخلق حلقة في شجرة التصنيفات")
        current = db.get(Category, current.parent_id)


@router.post("", response_model=ApiResponse[CategoryOut], status_code=201)
def create_category(
    payload: CategoryCreate,
    db: DbSession,
    user: StaffUser,
) -> ApiResponse[CategoryOut]:
    _validate_parent(db, payload.parent_id)
    cat = Category(**payload.model_dump())
    cat.slug = unique_slug(db, Category, payload.name)
    db.add(cat)
    db.flush()
    log_action(db, user_id=user.id, action=AuditAction.CREATE, entity_type="category", entity_id=cat.id,
               details={"name": cat.name})
    return ApiResponse(message="تم إنشاء التصنيف", data=_serialize(cat))


@router.get("/{category_id}", response_model=ApiResponse[CategoryOut])
def get_category(category_id: int, db: DbSession) -> ApiResponse[CategoryOut]:
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    return ApiResponse(data=_serialize(cat))


@router.put("/{category_id}", response_model=ApiResponse[CategoryOut])
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DbSession,
    user: StaffUser,
) -> ApiResponse[CategoryOut]:
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")

    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name"):
        cat.slug = unique_slug(db, Category, changes["name"], exclude_id=cat.id)
    if "parent_id" in changes:
        _validate_parent(db, changes["parent_id"], self_id=cat.id)
    for field_name, value in changes.items():
        setattr(cat, field_name, value)

    log_action(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="category", entity_id=cat.id)
    return ApiResponse(message="تم تحديث التصنيف", data=_serialize(cat))


@router.delete("/{category_id}", response_model=ApiResponse[None])
def delete_category(
    category_id: int,
    db: DbSession,
    user: StaffUser,
    force: bool = Query(default=False),
) -> ApiResponse[None]:
    """Deleting a category detaches its videos; children get promoted to root."""
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")

    linked = db.query(Video.id).filter(Video.category_id == cat.id).count()
    if linked > 0 and not force:
        raise HTTPException(
            status_code=409,
            detail=f"يحتوي هذا التصنيف على {linked} فيديو. استخدم force=true لحذفها معه.",
        )
    if force:
        db.query(Video).filter(Video.category_id == cat.id).update({Video.category_id: None})

    # Promote children instead of orphaning them.
    db.query(Category).filter(Category.parent_id == cat.id).update({Category.parent_id: cat.parent_id})

    db.delete(cat)
    log_action(db, user_id=user.id, action=AuditAction.DELETE, entity_type="category", entity_id=cat.id,
               details={"name": cat.name})
    return ApiResponse(message="تم حذف التصنيف")


@router.put("/reorder/all", response_model=ApiResponse[None])
def reorder_categories(
    body: ReorderRequest,
    db: DbSession,
    user: StaffUser,
) -> ApiResponse[None]:
    """Apply a new global ordering given the full ordered id list."""
    cats = {c.id: c for c in db.query(Category).filter(Category.id.in_(body.ids)).all()}
    for index, cid in enumerate(body.ids):
        if cid in cats:
            cats[cid].sort_order = index
    log_action(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="category",
               details={"reorder": len(body.ids)})
    return ApiResponse(message="تم حفظ الترتيب الجديد")
