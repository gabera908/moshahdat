"""Analytics schemas."""
from datetime import date, datetime

from pydantic import BaseModel

from app.models.video import VideoSourceType
from app.schemas.video import VideoListItem


class DashboardStats(BaseModel):
    total_videos: int
    published_videos: int
    draft_videos: int
    archived_videos: int
    total_views: int
    views_today: int
    total_categories: int
    total_playlists: int


class DailyViewsPoint(BaseModel):
    date: date
    views: int


class TopVideoItem(BaseModel):
    video: VideoListItem
    views: int


class BySourceItem(BaseModel):
    source_type: VideoSourceType
    count: int


class ByCategoryItem(BaseModel):
    category_id: int | None
    category_name: str | None
    count: int


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    details: dict | None
    created_at: datetime
