"""Dropbox provider: converts share links to direct/raw playback links."""
import re
from typing import ClassVar
from urllib.parse import urlparse

from app.models.video import VideoSourceType
from app.providers.base import BaseProvider, ProviderResult

_MEDIA_EXTS = (".mp4", ".webm", ".ogv", ".ogg", ".mov", ".m4v", ".m3u8")


class DropboxProvider(BaseProvider):
    name = "dropbox"
    source_type = VideoSourceType.DROPBOX
    PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^(?:https?://)?(?:www\.)?dropbox\.com/(?:s|scl/fi)/.+$", re.I),
    ]

    def analyze(self, url: str, match: re.Match[str]) -> ProviderResult:
        # Force direct download so the file can be streamed by the player.
        raw_url = match.group(0)
        raw_url = raw_url.replace("dl=0", "raw=1")
        if "dl=" not in raw_url:
            sep = "&" if "?" in raw_url else "?"
            raw_url = f"{raw_url}{sep}raw=1"

        path = urlparse(raw_url).path.lower()
        is_media = any(path.endswith(ext) for ext in _MEDIA_EXTS)

        return ProviderResult(
            source_type=self.source_type,
            valid=True,
            video_id=None,
            embed_url=raw_url,
            thumbnail_url=None,
            playable_mode="html5" if is_media else "iframe",
            message=(
                "تم التعرف على رابط Dropbox وتحويله إلى رابط مباشر."
                if is_media
                else "تم التعرف على رابط Dropbox؛ تأكد أنه ملف فيديو حتى يعمل التشغيل."
            ),
        )
