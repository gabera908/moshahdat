"""Tags: search + staff CRUD."""
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, Pagination, StaffUser
from app.models.tag import Tag
from app.schemas.common import ApiResponse
from app.schemas.taxonomy import TagCreate, TagOut, TagUpdate
from app.services.audit import AuditAction, log_action
from app.services.slugs import normalize_tag_name, unique_slug

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
def list_tags(
    db: DbSession,
    pagination: Pagination,
    q: str | None = Query(default=None, max_length=80),
) -> dict:
    """Public tag listing with optional prefix/substring search."""
    query = db.query(Tag).order_by(Tag.name.asc())
    if q:
        like = f"%{normalize_tag_name(q)}%"
        query = query.filter(Tag.name.ilike(like))
    total = query.count()
    tags = query.offset(pagination.offset).limit(pagination.page_size).all()
    from app.api.deps import paginate_response

    data = paginate_response(
        [TagOut.model_validate(t).model_dump(mode="json") for t in tags], total, pagination
    )
    return {"success": True, "message": "", "data": data}


@router.post("", response_model=ApiResponse[TagOut], status_code=201)
def create_tag(payload: TagCreate, db: DbSession, user: StaffUser) -> ApiResponse[TagOut]:
    name = normalize_tag_name(payload.name)
    existing = db.query(Tag).filter(Tag.name == name).first()
    if existing:
        return ApiResponse(message="الوسم موجود مسبقًا", data=TagOut.model_validate(existing))

    tag = Tag(name=name, slug=unique_slug(db, Tag, name))
    db.add(tag)
    db.flush()
    log_action(db, user_id=user.id, action=AuditAction.CREATE, entity_type="tag", entity_id=tag.id)
    return ApiResponse(message="تم إنشاء الوسم", data=TagOut.model_validate(tag))


@router.put("/{tag_id}", response_model=ApiResponse[TagOut])
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    db: DbSession,
    user: StaffUser,
) -> ApiResponse[TagOut]:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="الوسم غير موجود")
    name = normalize_tag_name(payload.name or "")
    clash = db.query(Tag.id).filter(Tag.name == name, Tag.id != tag_id).first()
    if clash:
        raise HTTPException(status_code=409, detail="يوجد وسم آخر بنفس الاسم")
    tag.name = name
    tag.slug = unique_slug(db, Tag, name, exclude_id=tag.id)
    log_action(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="tag", entity_id=tag.id)
    return ApiResponse(message="تم تحديث الوسم", data=TagOut.model_validate(tag))


@router.delete("/{tag_id}", response_model=ApiResponse[None])
def delete_tag(tag_id: int, db: DbSession, user: StaffUser) -> ApiResponse[None]:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="الوسم غير موجود")
    db.delete(tag)
    log_action(db, user_id=user.id, action=AuditAction.DELETE, entity_type="tag", entity_id=tag_id,
               details={"name": tag.name})
    return ApiResponse(message="تم حذف الوسم")
