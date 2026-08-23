"""Idempotent seed script: first admin user + optional demo content.

Usage:
    python -m scripts.seed            # create admin from env vars (if missing)
    python -m scripts.seed --demo     # also insert demo categories/videos/playlist
"""
import argparse
import sys

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import (
    Category,
    Playlist,
    PlaylistVideo,
    Tag,
    User,
    UserRole,
    Video,
    VideoSourceType,
    VideoStatus,
)
from app.services.slugs import unique_slug


def ensure_admin(db) -> None:
    settings = get_settings()
    existing = db.query(User).filter(User.username == settings.admin_username).first()
    if existing:
        print("Admin already exists - skipping.")
        return
    admin = User(
        username=settings.admin_username,
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password),
        full_name=settings.admin_full_name,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(f"Created admin user: {admin.username}")


DEMO_CATEGORIES = [
    {
        "name": "التدريب",
        "description": "ورش ودورات تدريبية",
        "children": [
            {"name": "الإعلام", "description": "مهارات إعلامية"},
            {"name": "التصوير", "description": "أساسيات التصوير"},
        ],
    },
    {"name": "البيئة", "description": "أفلام وتقارير بيئية", "children": []},
    {"name": "الفعاليات", "description": "تغطية الفعاليات", "children": []},
]

# Stable public sample sources.
# category_idx follows DFS order: 0=التدريب 1=الإعلام 2=التصوير 3=البيئة 4=الفعاليات
DEMO_VIDEOS = [
    {
        "title": "Big Buck Bunny",
        "description": "فيلم رسوم متحركة قصير مفتوح المصدر.",
        "source_type": VideoSourceType.YOUTUBE.value,
        "source_url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
        "category_idx": 3,  # البيئة
        "channel_name": "Blender Foundation",
        "tags": ["أنيميشن", "مفتوح المصدر"],
    },
    {
        "title": "عينة فيديو مباشر MP4",
        "description": "اختبار تشغيل الرابط المباشر داخل المشغل المدمج.",
        "source_type": VideoSourceType.DIRECT.value,
        "source_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "category_idx": 2,  # التصوير
        "channel_name": "إيكو ميديا",
        "tags": ["تجربة"],
    },
]


def seed_demo(db) -> None:
    if db.query(Video.id).count() > 0:
        print("Demo data skipped (videos table not empty).")
        return

    from datetime import datetime, timezone as tz

    from app.providers import detect_provider

    categories: list[Category] = []

    def _mk(spec: dict, parent_id: int | None = None) -> Category:
        cat = Category(
            name=spec["name"],
            slug=unique_slug(db, Category, spec["name"]),
            description=spec.get("description"),
            sort_order=len(categories),
            is_active=True,
            parent_id=parent_id,
        )
        db.add(cat)
        db.flush()
        categories.append(cat)
        for child in spec.get("children", []):
            _mk(child, parent_id=cat.id)
        return cat

    for spec in DEMO_CATEGORIES:
        _mk(spec)
    db.flush()

    videos = []
    for spec in DEMO_VIDEOS:
        result = detect_provider(spec["source_url"])
        info = result[1] if result else None
        v = Video(
            title=spec["title"],
            slug=unique_slug(db, Video, spec["title"]),
            description=spec["description"],
            source_type=VideoSourceType(spec["source_type"]),
            source_url=spec["source_url"],
            embed_url=info.embed_url if info else None,
            thumbnail_url=info.thumbnail_url if info else None,
            channel_name=spec.get("channel_name"),
            category_id=categories[spec["category_idx"]].id,
            status=VideoStatus.PUBLISHED,
            published_at=datetime.now(tz.utc),
        )
        for tag_name in spec["tags"]:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if tag is None:
                tag = Tag(name=tag_name, slug=unique_slug(db, Tag, tag_name))
                db.add(tag)
                db.flush()
            v.tags.append(tag)
        db.add(v)
        videos.append(v)
    db.flush()

    playlist = Playlist(
        title="أفضل اللحظات",
        slug=unique_slug(db, Playlist, "أفضل اللحظات"),
        description="مختارات من أحدث وأجمل الفيديوهات.",
        is_public=True,
    )
    db.add(playlist)
    db.flush()
    for i, v in enumerate(videos):
        db.add(PlaylistVideo(playlist_id=playlist.id, video_id=v.id, sort_order=i))

    db.commit()
    print("Demo content seeded.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed initial platform data")
    parser.add_argument("--demo", action="store_true", help="insert demo content")
    parser.add_argument("--init-tables", action="store_true", help="create tables if missing (dev only)")
    args = parser.parse_args()

    if args.init_tables:
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        ensure_admin(db)
        if args.demo:
            seed_demo(db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
