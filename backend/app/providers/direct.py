"""Direct URL provider: raw media files playable by the HTML5 player."""
import re
from typing import ClassVar
from urllib.parse import urlparse

from app.models.video import VideoSourceType
from app.providers.base import BaseProvider, ProviderResult

_MEDIA_EXTS = (".mp4", ".webm", ".ogv", ".ogg", ".mov", ".m4v", ".m3u8")


class DirectURLProvider(BaseProvider):
    name = "direct"
    source_type = VideoSourceType.DIRECT
    PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^https?://[^\s]+\.(mp4|webm|ogv|ogg|mov|m4v|m3u8)(\?[^\s]*)?$", re.I),
    ]

    def analyze(self, url: str, match: re.Match[str]) -> ProviderResult:
        ext = urlparse(url).path.rsplit(".", 1)[-1].lower()
        return ProviderResult(
            source_type=self.source_type,
            valid=True,
            video_id=None,
            embed_url=url,
            thumbnail_url=None,
            playable_mode="html5",
            message=f"تم التعرف على ملف فيديو مباشر ({ext.upper()}) وسيتم تشغيله بالمشغل المدمج.",
        )
