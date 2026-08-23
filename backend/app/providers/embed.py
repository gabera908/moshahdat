"""Generic embed provider: any HTTP(S) URL played inside an iframe.

Used as a fallback when the user explicitly selects "Embed URL" or when no
other provider matches. Some sites send X-Frame-Options/CSP that block
embedding; the API surfaces that risk to the admin instead of failing silently.
"""
import re
from typing import ClassVar

from app.models.video import VideoSourceType
from app.providers.base import BaseProvider, ProviderResult


class EmbedProvider(BaseProvider):
    name = "embed"
    source_type = VideoSourceType.EMBED
    PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^https?://.+$", re.I),
    ]

    def analyze(self, url: str, match: re.Match[str]) -> ProviderResult:
        return ProviderResult(
            source_type=self.source_type,
            valid=True,
            video_id=None,
            embed_url=match.group(0),
            thumbnail_url=None,
            playable_mode="iframe",
            message=(
                "سيتم تشغيل الرابط داخل إطار مدمج (iframe). "
                "بعض المواقع تمنع التضمين؛ استخدم زر المعاينة للتأكد."
            ),
        )
