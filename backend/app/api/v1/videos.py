"""Videos: public browsing, staff CRUD, publishing, views and bulk actions."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import (
    CurrentUser,
    DbSession,
    Pagination,
    PUBLISH_ROLES,
    STAFF_ROLES,
    get_current_user_optional,
    paginate_response,
)
from app.core.ratelimit import rate_limit
from app.models.category import Category
from app.models.playlist import PlaylistVideo
from app.models.tag import Tag
from app.models.user import User
from app.models.video import Video, VideoSourceType, VideoStatus
from app.providers import check_url
from app.schemas.common import ApiResponse
from app.schemas.video import (
    BulkActionRequest,
    CheckUrlRequest,
    CheckUrlResponse,
    TagBrief,
    VideoCreate,
    VideoListItem,
    VideoOut,
    VideoUpdate,
    ViewRegisterRequest,
)
from app.services.audit import AuditAction, log_action
from app.services.slugs import unique_slug
from app.services.views import register_view

router = APIRouter(prefix="/videos", tags=["videos"])

_SORTS = {
    "newest": Video.created_at.desc(),
    "oldest": Video.created_at.asc(),
    "views": Video.views_count.desc(),
    "title": Video.title.asc(),
}


def _is_staff(user: User | None) -> bool:
    return user is not None and user.role in STAFF_ROLES


def _card(v: Video) -> dict:
    item = VideoListItem(
        id=v.id,
        title=v.title,
        slug=v.slug,
        source_type=v.source_type,
        embed_url=v.embed_url,
        thumbnail_url=v.thumbnail_url,
        duration=v.duration,
        channel_name=v.channel_name,
        views_count=v.views_count,
        published_at=v.published_at,
        created_at=v.created_at,
        category=v.category,
        tags=[TagBrief.model_validate(t) for t in v.tags],
        is_featured=v.is_featured,
    )
    return item.model_dump(mode="json")


def _detail(v: Video) -> dict:
    return VideoOut.model_validate(v).model_dump(mode="json")


def _get_video_or_404(db: Session, video_id: int, include_deleted: bool = False) -> Video:
    video = db.query(Video).options(joinedload(Video.category)).get(video_id)
    if video is None or (video.deleted_at is not None and not include_deleted):
        raise HTTPException(status_code=404, detail="الفيديو غير موجود")
    return video


# ---------------------------------------------------------------- providers

@router.post("/check-url", response_model=ApiResponse[CheckUrlResponse])
def check_video_url(
    payload: CheckUrlRequest,
    request: Request,
) -> ApiResponse[CheckUrlResponse]:
    """Analyze a URL: detect provider, build embed/thumbnail, verify reachability."""
    rate_limit(request, "check-url", per_minute=30)
    result = check_url(payload.url)
    data = CheckUrlResponse(
        valid=result.valid,
        source_type=result.source_type,
        video_id=result.video_id,
        embed_url=result.embed_url,
        thumbnail_url=result.thumbnail_url,
        playable_mode=result.playable_mode,
        suggested_title=result.extras.get("suggested_title"),
        message=result.message,
    )
    return ApiResponse(success=result.valid, message=result.message, data=data)


# ---------------------------------------------------------------- public list

@router.get("")
def list_videos(
    db: DbSession,
    pagination: Pagination,
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, description="category slug or id"),
    tag: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    sort: str = Query(default="newest", pattern="^(newest|oldest|views|title)$"),
    featured: bool | None = None,
    source: str | None = Query(default=None),
    _user: User | None = Depends(get_current_user_optional),
) -> dict:
    """Public catalog. Non-published statuses require staff authentication."""
    staff = _is_staff(_user)

    query = db.query(Video).filter(Video.deleted_at.is_(None))

    if staff and status_filter:
        try:
            wanted = [VideoStatus(s.strip()) for s in status_filter.split(",")]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="حالة غير معروفة") from exc
        if any(s != VideoStatus.PUBLISHED for s in wanted):
            if not staff:
                raise HTTPException(status_code=403, detail="غير مسموح")
            if len(wanted) == 1:
                query = query.filter(Video.status == wanted[0])
            else:
                query = query.filter(Video.status.in_(wanted))
        else:
            query = query.filter(Video.status == VideoStatus.PUBLISHED)
    else:
        query = query.filter(Video.status == VideoStatus.PUBLISHED)

    if featured is not None:
        query = query.filter(Video.is_featured.is_(featured))

    if source:
        try:
            query = query.filter(Video.source_type == VideoSourceType(source))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="مصدر غير معروف") from exc

    if category:
        cat = None
        if category.isdigit():
            cat = db.get(Category, int(category))
        if cat is None:
            cat = db.query(Category).filter(Category.slug == category).first()
        if cat is None:
            raise HTTPException(status_code=404, detail="التصنيف غير موجود")
        query = query.filter(Video.category_id == cat.id)

    if tag:
        query = query.join(Video.tags).filter(Tag.slug == tag)

    if q:
        like = f"%{q.strip()}%"
        query = query.join(Category, isouter=True).filter(
            or_(
                Video.title.ilike(like),
                Video.description.ilike(like),
                Video.channel_name.ilike(like),
                Category.name.ilike(like),
                Video.tags.any(Tag.name.ilike(like)),
            )
        )

    total = query.count()
    order_clause = _SORTS.get(sort, _SORTS["newest"])
    rows = (
        query.options(joinedload(Video.category))
        .order_by(order_clause)
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    return {
        "success": True,
        "message": "",
        "data": paginate_response([_card(v) for v in rows], total, pagination),
    }


@router.get("/slug/{slug}")
def get_video_by_slug(slug: str, db: DbSession, _user: User | None = Depends(get_current_user_optional)) -> dict:
    """Public detail by SEO slug; drafts/archives visible to staff only."""
    video = (
        db.query(Video)
        .options(joinedload(Video.category))
        .filter(Video.slug == slug, Video.deleted_at.is_(None))
        .first()
    )
    if video is None:
        raise HTTPException(status_code=404, detail="الفيديو غير موجود")
    if video.status != VideoStatus.PUBLISHED and not _is_staff(_user):
        raise HTTPException(status_code=404, detail="الفيديو غير متاح")
    return {"success": True, "message": "", "data": _detail(video)}


# ---------------------------------------------------------------- view counting

@router.post("/{video_id}/view")
def record_view(video_id: int, payload: ViewRegisterRequest, request: Request, db: DbSession) -> dict:
    """Count one view per anonymous session per hour; raw IPs are hashed."""
    rate_limit(request, "view", per_minute=120)
    video = db.query(Video.id).filter(
        Video.id == video_id, Video.status == VideoStatus.PUBLISHED, Video.deleted_at.is_(None)
    ).first()
    if video is None:
        raise HTTPException(status_code=404, detail="الفيديو غير متاح")

    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    counted = register_view(
        db,
        video_id=video_id,
        session_id=payload.session_id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    return {"success": True, "message": "", "data": {"counted": counted}}


# ---------------------------------------------------------------- staff CRUD

@router.post("", response_model=ApiResponse[dict], status_code=201)
def create_video(payload: VideoCreate, db: DbSession, user: CurrentUser) -> ApiResponse[dict]:
    from app.api.deps import WRITE_ROLES

    if user.role not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="ليست لديك صلاحية إنشاء فيديو")

    if payload.category_id is not None and db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")

    # Auto-fill embed/thumbnail from provider when possible.
    result = check_url(payload.source_url, verify_reachable=False)
    embed_url = payload.embed_url or (result.embed_url if result.valid else None)
    thumbnail_url = payload.thumbnail_url or (result.thumbnail_url if result.valid else None)

    video = Video(
        **payload.model_dump(exclude={"tag_ids", "embed_url", "thumbnail_url"}),
        slug=unique_slug(db, Video, payload.title),
        embed_url=embed_url,
        thumbnail_url=thumbnail_url,
        created_by=user.id,
    )
    if payload.status == VideoStatus.PUBLISHED:
        video.published_at = datetime.now(timezone.utc)

    tags = db.query(Tag).filter(Tag.id.in_(payload.tag_ids)).all() if payload.tag_ids else []
    video.tags = list(tags)

    db.add(video)
    db.flush()
    log_action(db, user_id=user.id, action=AuditAction.CREATE, entity_type="video", entity_id=video.id,
               details={"title": video.title, "source": video.source_type.value})
    return ApiResponse(message="تم إنشاء الفيديو", data=_detail(video))


@router.get("/admin/all")
def admin_list(
    db: DbSession,
    pagination: Pagination,
    _staff: CurrentUser,
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
    category_id: int | None = None,
    sort: str = Query(default="newest", pattern="^(newest|oldest|views|title)$"),
) -> dict:
    """Full management listing including drafts/archived/deleted flag."""
    query = db.query(Video).options(joinedload(Video.category))
    if status_filter:
        try:
            query = query.filter(Video.status == VideoStatus(status_filter))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="حالة غير معروفة") from exc
    if category_id:
        query = query.filter(Video.category_id == category_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Video.title.ilike(like), Video.description.ilike(like), Video.channel_name.ilike(like)))

    total = query.count()
    rows = (
        query.order_by(_SORTS.get(sort, _SORTS["newest"]))
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    return {
        "success": True,
        "message": "",
        "data": paginate_response([_detail(v) for v in rows], total, pagination),
    }


@router.get("/{video_id}", response_model=ApiResponse[dict])
def get_video(video_id: int, db: DbSession, _staff: CurrentUser) -> ApiResponse[dict]:
    video = _get_video_or_404(db, video_id)
    return ApiResponse(data=_detail(video))


@router.put("/{video_id}", response_model=ApiResponse[dict])
def update_video(
    video_id: int,
    payload: VideoUpdate,
    db: DbSession,
    user: CurrentUser,
) -> ApiResponse[dict]:
    from app.api.deps import WRITE_ROLES

    video = _get_video_or_404(db, video_id)
    if user.role not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="ليست لديك صلاحية تعديل الفيديو")

    changes = payload.model_dump(exclude_unset=True)
    tag_ids = changes.pop("tag_ids", None)
    new_status = changes.pop("status", None)

    if "category_id" in changes:
        cid = changes["category_id"]
        if cid is not None and db.get(Category, cid) is None:
            raise HTTPException(status_code=404, detail="التصنيف غير موجود")

    if changes.get("title"):
        video.slug = unique_slug(db, Video, changes["title"], exclude_id=video.id)

    for field_name, value in changes.items():
        setattr(video, field_name, value)

    if tag_ids is not None:
        video.tags = list(db.query(Tag).filter(Tag.id.in_(tag_ids)).all())

    if new_status:
        # Handles published_at stamping for first publish.
        _set_status(video, new_status)

    db.flush()
    log_action(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="video", entity_id=video.id)
    return ApiResponse(message="تم تحديث الفيديو", data=_detail(video))


@router.delete("/{video_id}", response_model=ApiResponse[None])
def delete_video(
    video_id: int,
    db: DbSession,
    user: CurrentUser,
    hard: bool = Query(default=False, description="permanent delete (admin only)"),
) -> ApiResponse[None]:
    """Soft delete by default; hard delete restricted to admins."""
    video = _get_video_or_404(db, video_id, include_deleted=hard)
    from app.api.deps import ADMIN_ROLES, WRITE_ROLES

    if hard:
        if user.role not in ADMIN_ROLES:
            raise HTTPException(status_code=403, detail="الحذف النهائي متاح للمدير فقط")
        db.query(PlaylistVideo).filter(PlaylistVideo.video_id == video.id).delete()
        db.delete(video)
        message = "تم حذف الفيديو نهائيًا"
    else:
        if user.role not in WRITE_ROLES:
            raise HTTPException(status_code=403, detail="ليست لديك صلاحية الحذف")
        if video.deleted_at is None:
            video.deleted_at = datetime.now(timezone.utc)
        message = "تم نقل الفيديو إلى المحذوفات"

    log_action(db, user_id=user.id, action=AuditAction.DELETE, entity_type="video", entity_id=video_id,
               details={"hard": hard})
    return ApiResponse(message=message)


@router.post("/bulk", response_model=ApiResponse[dict])
def bulk_action(body: BulkActionRequest, db: DbSession, user: CurrentUser) -> ApiResponse[dict]:
    """Bulk publish/unpublish/archive/delete."""
    from app.api.deps import ADMIN_ROLES, WRITE_ROLES

    if body.action == "delete":
        if user.role not in WRITE_ROLES:
            raise HTTPException(status_code=403, detail="ليست لديك صلاحية الحذف")
    elif body.action in ("publish", "unpublish", "archive"):
        if user.role not in PUBLISH_ROLES:
            raise HTTPException(status_code=403, detail="ليست لديك صلاحية تغيير حالة النشر")

    now = datetime.now(timezone.utc)
    affected = 0
    vids = db.query(Video).filter(Video.id.in_(body.ids), Video.deleted_at.is_(None)).all()

    for v in vids:
        if body.action == "delete":
            v.deleted_at = now
        elif body.action == "publish":
            v.status = VideoStatus.PUBLISHED
            if v.published_at is None:
                v.published_at = now
        elif body.action == "unpublish":
            v.status = VideoStatus.DRAFT
        elif body.action == "archive":
            v.status = VideoStatus.ARCHIVED
        affected += 1

    log_action(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="video",
               details={"bulk": body.action, "count": affected})
    return ApiResponse(message=f"تم تنفيذ العملية على {affected} عنصر", data={"affected": affected})


# ---------------------------------------------------------------- lifecycle

def _set_status(video: Video, new_status: VideoStatus) -> str | None:
    if video.status == new_status:
        return None
    video.status = new_status
    if new_status == VideoStatus.PUBLISHED and video.published_at is None:
        video.published_at = datetime.now(timezone.utc)
    return new_status.value


def _lifecycle(video_id: int, db: DbSession, user: CurrentUser, action: AuditAction, target: VideoStatus) -> ApiResponse[dict]:
    """Apply a status transition; role checks are done by each endpoint."""
    video = _get_video_or_404(db, video_id)
    changed = _set_status(video, target)
    db.flush()
    log_action(db, user_id=user.id, action=action, entity_type="video", entity_id=video.id)
    messages = {
        AuditAction.PUBLISH: "تم نشر الفيديو",
        AuditAction.UNPUBLISH: "تم إلغاء نشر الفيديو",
        AuditAction.ARCHIVE: "تم أرشفة الفيديو",
    }
    if changed is None:
        return ApiResponse(message="الفيديو في هذه الحالة مسبقًا", data=_detail(video))
    return ApiResponse(message=messages[action], data=_detail(video))


@router.post("/{video_id}/publish", response_model=ApiResponse[dict])
def publish_video(video_id: int, db: DbSession, user: CurrentUser) -> ApiResponse[dict]:
    if user.role not in PUBLISH_ROLES:
        raise HTTPException(status_code=403, detail="ليست لديك صلاحية النشر")
    return _lifecycle(video_id, db, user, AuditAction.PUBLISH, VideoStatus.PUBLISHED)


@router.post("/{video_id}/unpublish", response_model=ApiResponse[dict])
def unpublish_video(video_id: int, db: DbSession, user: CurrentUser) -> ApiResponse[dict]:
    if user.role not in PUBLISH_ROLES:
        raise HTTPException(status_code=403, detail="ليست لديك صلاحية النشر")
    return _lifecycle(video_id, db, user, AuditAction.UNPUBLISH, VideoStatus.DRAFT)


@router.post("/{video_id}/archive", response_model=ApiResponse[dict])
def archive_video(video_id: int, db: DbSession, user: CurrentUser) -> ApiResponse[dict]:
    if user.role not in PUBLISH_ROLES:
        raise HTTPException(status_code=403, detail="ليست لديك صلاحية الأرشفة")
    return _lifecycle(video_id, db, user, AuditAction.ARCHIVE, VideoStatus.ARCHIVED)


@router.post("/{video_id}/duplicate", response_model=ApiResponse[dict], status_code=201)
def duplicate_video(video_id: int, db: DbSession, user: CurrentUser) -> ApiResponse[dict]:
    from app.api.deps import WRITE_ROLES

    if user.role not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="ليست لديك صلاحية الإنشاء")

    src = _get_video_or_404(db, video_id)
    clone = Video(
        title=f"{src.title} (نسخة)",
        slug=unique_slug(db, Video, f"{src.title} نسخة {datetime.now(timezone.utc).timestamp():.0f}"[:150]),
        description=src.description,
        source_type=src.source_type,
        source_url=src.source_url,
        embed_url=src.embed_url,
        thumbnail_url=src.thumbnail_url,
        duration=src.duration,
        category_id=src.category_id,
        status=VideoStatus.DRAFT,
        created_by=user.id,
    )
    clone.tags = list(src.tags)
    db.add(clone)
    db.flush()
    log_action(db, user_id=user.id, action=AuditAction.DUPLICATE, entity_type="video",
               entity_id=clone.id, details={"from": src.id})
    return ApiResponse(message="تم إنشاء نسخة كمسودة", data=_detail(clone))
