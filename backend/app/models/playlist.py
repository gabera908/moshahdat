"""Playlist model and its ordered video membership."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, BigIntPK


class Playlist(Base):
    """A curated, ordered list of videos."""

    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(400), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048), default=None)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items = relationship(
        "PlaylistVideo",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistVideo.sort_order",
        lazy="selectin",
    )

    @property
    def videos(self) -> list:
        """Videos in stored order."""
        return [item.video for item in self.items]

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Playlist {self.slug}>"


class PlaylistVideo(Base):
    """Membership row linking a playlist to a video with ordering."""

    __tablename__ = "playlist_videos"
    __table_args__ = (
        UniqueConstraint("playlist_id", "video_id", name="uq_playlist_video"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    playlist_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("playlists.id", ondelete="CASCADE"), index=True
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    playlist = relationship("Playlist", back_populates="items")
    video = relationship("Video", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PlaylistVideo pl={self.playlist_id} v={self.video_id} ord={self.sort_order}>"
