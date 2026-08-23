"""Vimeo provider."""
import re
from typing import ClassVar

from app.models.video import VideoSourceType
from app.providers.base import BaseProvider, ProviderResult


class VimeoProvider(BaseProvider):
    name = "vimeo"
    source_type = VideoSourceType.VIMEO
    PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^(?:https?://)?(?:www\.|player\.)?vimeo\.com/(?:video/)?(\d{6,})(?:[/?#].*)?$", re.I),
    ]

    def analyze(self, url: str, match: re.Match[str]) -> ProviderResult:
        video_id = match.group(1)
        return ProviderResult(
            source_type=self.source_type,
            valid=True,
            video_id=video_id,
            embed_url=f"https://player.vimeo.com/video/{video_id}",
            thumbnail_url=None,
            playable_mode="iframe",
            message="تم التعرف على فيديو Vimeo بنجاح.",
            extras={"canonical": f"https://vimeo.com/{video_id}"},
        )
