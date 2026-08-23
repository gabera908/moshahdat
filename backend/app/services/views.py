"""View tracking: dedupe per session, hash IPs, never store raw addresses."""
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.video import Video
from app.models.video_view import VideoView

DEDUPE_WINDOW = timedelta(hours=1)
_IP_SALT = b"vp-mvp-static-salt-change-me"


def hash_ip(ip: str) -> str:
    """One-way salted hash so raw IPs are never persisted."""
    return hashlib.sha256(_IP_SALT + ip.encode("utf-8", "ignore")).hexdigest()[:64]


def register_view(
    db: Session,
    *,
    video_id: int,
    session_id: str,
    ip: str | None,
    user_agent: str | None,
) -> bool:
    """Count a view unless the same session already viewed it recently.

    Returns True when a new view row was recorded.
    """
    now = datetime.now(timezone.utc)
    recent = (
        db.query(VideoView.id)
        .filter(
            VideoView.video_id == video_id,
            VideoView.session_id == session_id,
            VideoView.viewed_at >= now - DEDUPE_WINDOW,
        )
        .first()
    )
    if recent is not None:
        return False

    db.add(
        VideoView(
            video_id=video_id,
            session_id=session_id,
            ip_hash=hash_ip(ip) if ip else None,
            user_agent=(user_agent or "")[:512] or None,
            viewed_at=now,
        )
    )
    db.execute(
        update(Video).where(Video.id == video_id).values(views_count=Video.views_count + 1)
    )
    db.flush()
    return True
