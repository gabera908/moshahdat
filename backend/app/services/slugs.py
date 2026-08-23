"""Slug utilities: unicode-aware, Arabic-friendly, uniqueness-enforced."""
import re
import unicodedata

from sqlalchemy.orm import Session

_SLUG_STRIP_RE = re.compile(r"[^\w\s\u0600-\u06FF-]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"[\s_]+")


def base_slug(text: str) -> str:
    """Build a readable, SEO-friendly slug from any title (Arabic or Latin)."""
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = _SLUG_STRIP_RE.sub("", text)
    text = _WHITESPACE_RE.sub("-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:180] or "item"


def unique_slug(db: Session, model: type, text: str, exclude_id: int | None = None) -> str:
    """Ensure the slug is unique for `model`, appending -2, -3... when needed."""
    candidate = base_slug(text)

    def _exists(slug_value: str) -> bool:
        q = db.query(model.id).filter(model.slug == slug_value)
        if exclude_id is not None:
            q = q.filter(model.id != exclude_id)
        return db.query(q.exists()).scalar()

    if not _exists(candidate):
        return candidate

    counter = 2
    while True:
        alt = f"{candidate}-{counter}"
        if not _exists(alt):
            return alt
        counter += 1


def normalize_tag_name(name: str) -> str:
    """Canonical tag key used for dedupe."""
    cleaned = unicodedata.normalize("NFKC", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned
