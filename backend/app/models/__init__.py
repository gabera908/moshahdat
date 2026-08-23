"""Import all models so Alembic/Base.metadata sees the full schema."""
from app.models.audit_log import AuditAction, AuditLog
from app.models.category import Category
from app.models.playlist import Playlist, PlaylistVideo
from app.models.tag import Tag
from app.models.user import User, UserRole
from app.models.video import Video, VideoSourceType, VideoStatus, video_tags
from app.models.video_view import VideoView

__all__ = [
    "AuditAction",
    "AuditLog",
    "Category",
    "Playlist",
    "PlaylistVideo",
    "Tag",
    "User",
    "UserRole",
    "Video",
    "VideoSourceType",
    "VideoStatus",
    "VideoView",
    "video_tags",
]
