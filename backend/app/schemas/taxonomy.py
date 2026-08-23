"""Category, tag and playlist schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.video import VideoListItem


# ---------- Category ----------
class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=1024)
    sort_order: int = 0
    is_active: bool = True
    parent_id: int | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    parent_id: int | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    image_url: str | None
    sort_order: int
    is_active: bool
    parent_id: int | None
    created_at: datetime


class ReorderRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


# ---------- Tag ----------
class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


# ---------- Playlist ----------
class PlaylistBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    thumbnail_url: str | None = Field(default=None, max_length=2048)
    is_public: bool = True


class PlaylistCreate(PlaylistBase):
    video_ids: list[int] = []


class PlaylistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    thumbnail_url: str | None = None
    is_public: bool | None = None


class PlaylistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    description: str | None
    thumbnail_url: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime


class PlaylistDetailOut(PlaylistOut):
    videos: list[VideoListItem] = []


class PlaylistVideosRequest(BaseModel):
    """Ordered video ids — sets membership AND order."""

    video_ids: list[int] = Field(max_length=1000)
