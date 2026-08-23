"""YouTube provider: watch / youtu.be / shorts / embed links."""
import re
from typing import ClassVar

from app.models.video import VideoSourceType
from app.providers.base import BaseProvider, ProviderResult

_YT_ID = r"[A-Za-z0-9_-]{11}"


class YouTubeProvider(BaseProvider):
    name = "youtube"
    source_type = VideoSourceType.YOUTUBE
    PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(rf"^(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?.*v=({_YT_ID})", re.I),
        re.compile(rf"^(?:https?://)?youtu\.be/({_YT_ID})(?:\?.*)?$", re.I),
        re.compile(rf"^(?:https?://)?(?:www\.)?youtube\.com/(?:shorts|embed|v|live)/({_YT_ID})(?:\?.*)?$", re.I),
    ]

    def analyze(self, url: str, match: re.Match[str]) -> ProviderResult:
        video_id = match.group(1)
        return ProviderResult(
            source_type=self.source_type,
            valid=True,
            video_id=video_id,
            embed_url=f"https://www.youtube.com/embed/{video_id}?rel=0",
            thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            playable_mode="iframe",
            message="تم التعرف على فيديو يوتيوب بنجاح.",
            extras={"canonical": f"https://www.youtube.com/watch?v={video_id}"},
        )
