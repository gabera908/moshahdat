"""Video-related schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.video import VideoSourceType, VideoStatus


# ---------- Provider / check-url ----------
class CheckUrlRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class CheckUrlResponse(BaseModel):
    valid: bool
    source_type: VideoSourceType | None = None
    video_id: str | None = None
    embed_url: str | None = None
    thumbnail_url: str | None = None
    playable_mode: str = "unknown"
    message: str = ""


# ---------- CRUD payloads ----------
class TagBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str


class VideoBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    source_type: VideoSourceType
    source_url: str = Field(min_length=1, max_length=2048)
    embed_url: str | None = Field(default=None, max_length=2048)
    thumbnail_url: str | None = Field(default=None, max_length=2048)
    duration: int | None = Field(default=None, ge=0)
    channel_name: str | None = Field(default=None, max_length=200)
    category_id: int | None = None
    status: VideoStatus = VideoStatus.DRAFT
    is_featured: bool = False


class VideoCreate(VideoBase):
    tag_ids: list[int] = []


class VideoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    source_type: VideoSourceType | None = None
    source_url: str | None = Field(default=None, min_length=1, max_length=2048)
    embed_url: str | None = Field(default=None, max_length=2048)
    thumbnail_url: str | None = Field(default=None, max_length=2048)
    duration: int | None = Field(default=None, ge=0)
    channel_name: str | None = Field(default=None, max_length=200)
    category_id: int | None = None
    is_featured: bool | None = None
    status: VideoStatus | None = None
    published_at: datetime | None = None
    tag_ids: list[int] | None = None


class CategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str


class VideoOut(BaseModel):
    """Full representation for admin/detail views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    description: str | None
    source_type: VideoSourceType
    source_url: str
    embed_url: str | None
    thumbnail_url: str | None
    duration: int | None
    channel_name: str | None
    category_id: int | None
    category: CategoryBrief | None
    tags: list[TagBrief] = []
    status: VideoStatus
    is_featured: bool
    views_count: int
    published_at: datetime | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class VideoListItem(BaseModel):
    """Compact public card representation."""

    id: int
    title: str
    slug: str
    source_type: VideoSourceType
    embed_url: str | None
    thumbnail_url: str | None
    duration: int | None
    channel_name: str | None = None
    views_count: int
    published_at: datetime | None
    created_at: datetime
    category: CategoryBrief | None = None
    tags: list[TagBrief] = []
    is_featured: bool = False


class BulkActionRequest(BaseModel):
    action: str = Field(pattern="^(publish|unpublish|archive|delete)$")
    ids: list[int] = Field(min_length=1, max_length=200)


class ViewRegisterRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
