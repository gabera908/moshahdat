"""Analytics & dashboard statistics (staff only)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func as sa_func
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, PublisherUser
from app.models.audit_log import AuditLog
from app.models.playlist import Playlist
from app.models.category import Category
from app.models.video import Video, VideoStatus, VideoSourceType
from app.models.video_view import VideoView

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(db: DbSession, _staff: PublisherUser) -> dict:
    """Top-level counters for the admin dashboard."""
    total_videos = db.query(Video.id).filter(Video.deleted_at.is_(None)).count()
    published = db.query(Video.id).filter(
        Video.status == VideoStatus.PUBLISHED, Video.deleted_at.is_(None)
    ).count()
    drafts = db.query(Video.id).filter(
        Video.status == VideoStatus.DRAFT, Video.deleted_at.is_(None)
    ).count()
    archived = db.query(Video.id).filter(
        Video.status == VideoStatus.ARCHIVED, Video.deleted_at.is_(None)
    ).count()
    total_views = (
        db.query(sa_func.coalesce(sa_func.sum(Video.views_count), 0))
        .filter(Video.deleted_at.is_(None))
        .scalar()
    )

    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    views_today = (
        db.query(VideoView.id).filter(VideoView.viewed_at >= day_start).count()
    )

    data = {
        "total_videos": total_videos,
        "published_videos": published,
        "draft_videos": drafts,
        "archived_videos": archived,
        "total_views": int(total_views or 0),
        "views_today": views_today,
        "total_categories": db.query(Category.id).count(),
        "total_playlists": db.query(Playlist.id).count(),
    }
    return {"success": True, "message": "", "data": data}


@router.get("/views/daily")
def daily_views(
    db: DbSession,
    _staff: PublisherUser,
    days: int = Query(default=30, ge=7, le=365),
    video_id: int | None = None,
) -> dict:
    """Views per day over the last N days (aggregated in Python for portability)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(VideoView.viewed_at).filter(VideoView.viewed_at >= since)
    if video_id:
        query = query.filter(VideoView.video_id == video_id)

    buckets: dict[str, int] = {}
    for (viewed_at,) in query.all():
        key = viewed_at.date().isoformat()
        buckets[key] = buckets.get(key, 0) + 1

    points = []
    cursor = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date()
    today = datetime.now(timezone.utc).date()
    while cursor <= today:
        key = cursor.isoformat()
        points.append({"date": key, "views": buckets.get(key, 0)})
        cursor += timedelta(days=1)

    return {"success": True, "message": "", "data": {"items": points}}


@router.get("/top-videos")
def top_videos(db: DbSession, _staff: PublisherUser, limit: int = Query(default=10, ge=1, le=50)) -> dict:
    """Most-viewed videos."""
    from app.api.v1.videos import _card

    rows = (
        db.query(Video)
        .options(joinedload(Video.category))
        .filter(Video.deleted_at.is_(None))
        .order_by(Video.views_count.desc())
        .limit(limit)
        .all()
    )
    items = [{"video": _card(v), "views": v.views_count} for v in rows]
    return {"success": True, "message": "", "data": {"items": items}}


@router.get("/by-source")
def by_source(db: DbSession, _staff: PublisherUser) -> dict:
    """Video count grouped by source type."""
    rows = (
        db.query(Video.source_type, sa_func.count(Video.id))
        .filter(Video.deleted_at.is_(None))
        .group_by(Video.source_type)
        .all()
    )
    return {"success": True, "message": "", "data": {"items": [
        {"source_type": st.value, "count": cnt} for st, cnt in rows
    ]}}


@router.get("/by-category")
def by_category(db: DbSession, _staff: PublisherUser) -> dict:
    """Published video count grouped by category (includes uncategorized)."""
    rows = (
        db.query(Video.category_id, sa_func.count(Video.id))
        .filter(Video.deleted_at.is_(None), Video.status == VideoStatus.PUBLISHED)
        .group_by(Video.category_id)
        .all()
    )
    cats = {c.id: c.name for c in db.query(Category).all()}
    items = [
        {
            "category_id": cid,
            "category_name": cats.get(cid),
            "count": cnt,
        }
        for cid, cnt in rows
    ]
    return {"success": True, "message": "", "data": {"items": items}}
