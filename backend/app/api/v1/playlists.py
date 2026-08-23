"""Playlists: public reads + staff CRUD + ordered membership."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import joinedload

from app.api.deps import (
    DbSession,
    Pagination,
    PublisherUser,
    StaffUser,
    STAFF_ROLES,
    get_current_user_optional,
    paginate_response,
)
from app.models.playlist import Playlist, PlaylistVideo
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.schemas.common import ApiResponse
from app.schemas.taxonomy import (
    PlaylistCreate,
    PlaylistDetailOut,
    PlaylistOut,
    PlaylistUpdate,
    PlaylistVideosRequest,
)
from app.services.audit import AuditAction, log_action
from app.services.slugs import unique_slug

router = APIRouter(prefix="/playlists", tags=["playlists"])


def _serialize(p: Playlist) -> dict:
    return PlaylistOut.model_validate(p).model_dump(mode="json")


def _serialize_detail(p: Playlist) -> dict:
    from app.api.v1.videos import _card

    detail = PlaylistDetailOut(
        id=p.id,
        title=p.title,
        slug=p.slug,
        description=p.description,
        thumbnail_url=p.thumbnail_url,
        is_public=p.is_public,
        created_at=p.created_at,
        updated_at=p.updated_at,
        videos=[],
    )
    data = detail.model_dump(mode="json")
    data["videos"] = [_card(item.video) for item in p.items if item.video is not None]
    return data


def _get_or_404(db: DbSession, playlist_id: int) -> Playlist:
    playlist = db.query(Playlist).get(playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="قائمة التشغيل غير موجودة")
    return playlist


@router.get("")
def list_playlists(
    db: DbSession,
    pagination: Pagination,
    include_private: bool = Query(default=False),
    _user: User | None = Depends(get_current_user_optional),
) -> dict:
    """Public listing of playlists; private ones visible to staff only."""
    query = db.query(Playlist).order_by(Playlist.created_at.desc())
    is_staff = _user is not None and _user.role in STAFF_ROLES
    if not (include_private and is_staff):
        query = query.filter(Playlist.is_public.is_(True))

    total = query.count()
    rows = query.offset(pagination.offset).limit(pagination.page_size).all()

    items = []
    for p in rows:
        item = _serialize(p)
        item["videos_count"] = len(p.items)
        first_video_thumb = next((i.video for i in p.items if i.video and i.video.status == VideoStatus.PUBLISHED), None)
        if item.get("thumbnail_url") is None and first_video_thumb is not None:
            item["thumbnail_url"] = first_video_thumb.thumbnail_url
        items.append(item)

    return {"success": True, "message": "", "data": paginate_response(items, total, pagination)}


@router.post("", response_model=ApiResponse[dict], status_code=201)
def create_playlist(payload: PlaylistCreate, db: DbSession, user: StaffUser) -> ApiResponse[dict]:
    playlist = Playlist(
        title=payload.title,
        slug=unique_slug(db, Playlist, payload.title),
        description=payload.description,
        thumbnail_url=payload.thumbnail_url,
        is_public=payload.is_public,
    )
    db.add(playlist)
    db.flush()

    if payload.video_ids:
        _set_membership(db, user.id, playlist, payload.video_ids)

    log_action(db, user_id=user.id, action=AuditAction.CREATE, entity_type="playlist",
               entity_id=playlist.id, details={"title": playlist.title})
    return ApiResponse(message="تم إنشاء القائمة", data=_serialize_detail(playlist))


def _set_membership(db: DbSession, user_id: int | None, playlist: Playlist, video_ids: list[int]) -> None:
    """Replace membership with the given ordered ids (deduped)."""
    seen: set[int] = set()
    unique_ids: list[int] = []
    for vid in video_ids:
        if vid not in seen:
            seen.add(vid)
            unique_ids.append(vid)

    existing_videos = (
        db.query(Video.id).filter(Video.id.in_(unique_ids), Video.deleted_at.is_(None)).count()
    )
    missing = len(unique_ids) - existing_videos
    if missing > 0:
        raise HTTPException(status_code=404, detail=f"بعض الفيديوهات غير موجودة ({missing})")

    playlist.items.clear()
    db.flush()
    for order, vid in enumerate(unique_ids):
        db.add(PlaylistVideo(playlist_id=playlist.id, video_id=vid, sort_order=order))
    db.flush()
    db.expire(playlist)  # force re-load of the items relationship


@router.get("/slug/{slug}")
def get_playlist_by_slug(slug: str, db: DbSession, _user: User | None = Depends(get_current_user_optional)) -> dict:
    """Public detail with ordered published videos."""
    playlist = (
        db.query(Playlist)
        .options(joinedload(Playlist.items).joinedload(PlaylistVideo.video))
        .filter(Playlist.slug == slug)
        .first()
    )
    if playlist is None:
        raise HTTPException(status_code=404, detail="قائمة التشغيل غير موجودة")

    is_staff = _user is not None and _user.role in STAFF_ROLES
    if not playlist.is_public and not is_staff:
        raise HTTPException(status_code=404, detail="قائمة التشغيل غير متاحة")

    # Only published videos are shown publicly.
    if not is_staff:
        playlist.items = [i for i in playlist.items if i.video and i.video.status == VideoStatus.PUBLISHED]

    return {"success": True, "message": "", "data": _serialize_detail(playlist)}


@router.get("/{playlist_id}", response_model=ApiResponse[dict])
def get_playlist(playlist_id: int, db: DbSession, _staff: PublisherUser) -> ApiResponse[dict]:
    return ApiResponse(data=_serialize_detail(_get_or_404(db, playlist_id)))


@router.put("/{playlist_id}", response_model=ApiResponse[dict])
def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdate,
    db: DbSession,
    user: StaffUser,
) -> ApiResponse[dict]:
    playlist = _get_or_404(db, playlist_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("title"):
        playlist.slug = unique_slug(db, Playlist, changes["title"], exclude_id=playlist.id)
    for field_name, value in changes.items():
        setattr(playlist, field_name, value)

    log_action(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="playlist", entity_id=playlist.id)
    return ApiResponse(message="تم تحديث القائمة", data=_serialize_detail(playlist))


@router.put("/{playlist_id}/videos", response_model=ApiResponse[dict])
def set_playlist_videos(
    playlist_id: int,
    payload: PlaylistVideosRequest,
    db: DbSession,
    user: StaffUser,
) -> ApiResponse[dict]:
    """Set exact membership AND order (drag & drop result)."""
    playlist = _get_or_404(db, playlist_id)
    _set_membership(db, user.id, playlist, payload.video_ids)
    log_action(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="playlist",
               entity_id=playlist.id, details={"set_videos": len(payload.video_ids)})
    return ApiResponse(message="تم تحديث فيديوهات القائمة", data=_serialize_detail(playlist))


@router.delete("/{playlist_id}", response_model=ApiResponse[None])
def delete_playlist(playlist_id: int, db: DbSession, user: StaffUser) -> ApiResponse[None]:
    playlist = _get_or_404(db, playlist_id)
    db.delete(playlist)
    log_action(db, user_id=user.id, action=AuditAction.DELETE, entity_type="playlist", entity_id=playlist_id,
               details={"title": playlist.title})
    return ApiResponse(message="تم حذف القائمة")
