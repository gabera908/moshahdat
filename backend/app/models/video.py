"""Video model, statuses and source types."""
import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, BigIntPK


class VideoStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class VideoSourceType(str, enum.Enum):
    YOUTUBE = "youtube"
    GDRIVE = "gdrive"
    VIMEO = "vimeo"
    DROPBOX = "dropbox"
    DIRECT = "direct"
    EMBED = "embed"


video_tags = Table(
    "video_tags",
    Base.metadata,
    Column(
        "video_id",
        BigIntPK,
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        BigInteger,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Video(Base):
    """A video entry referencing an external source (no uploads in MVP)."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    slug: Mapped[str] = mapped_column(String(600), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    source_type: Mapped[VideoSourceType] = mapped_column(
        Enum(VideoSourceType, native_enum=False, length=20, values_callable=lambda e: [i.value for i in e])
    )
    source_url: Mapped[str] = mapped_column(String(2048))
    embed_url: Mapped[str | None] = mapped_column(String(2048), default=None)
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048), default=None)
    duration: Mapped[int | None] = mapped_column(Integer, default=None)  # seconds
    channel_name: Mapped[str | None] = mapped_column(String(200), default=None)

    category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="SET NULL"), default=None, index=True
    )
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, native_enum=False, length=20, values_callable=lambda e: [i.value for i in e]),
        default=VideoStatus.DRAFT,
        index=True,
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    views_count: Mapped[int] = mapped_column(BigInteger, default=0, index=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None, index=True)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category = relationship("Category", lazy="joined")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=video_tags, lazy="selectin", order_by="Tag.name"
    )

    __table_args__ = (
        Index("ix_videos_status_created", "status", "created_at"),
        Index("ix_videos_category_status", "category_id", "status"),
        {"comment": "Videos are external-source references; nothing is uploaded."},
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Video {self.slug} [{self.status.value}]>"
