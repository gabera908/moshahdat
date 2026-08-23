"""Video view tracking model (privacy-aware)."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base, BigIntPK


def new_session_id() -> str:
    """Generate an anonymous session identifier."""
    return uuid.uuid4().hex


class VideoView(Base):
    """A single counted view. Raw IPs are never stored â€” only a salted hash."""

    __tablename__ = "video_views"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(512), default=None)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("ix_video_views_video_time", "video_id", "viewed_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<VideoView v={self.video_id} at={self.viewed_at}>"
