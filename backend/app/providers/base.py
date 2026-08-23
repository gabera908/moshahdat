"""Base abstraction for all video source providers.

Every provider is responsible for:
- detecting whether a URL belongs to it
- extracting a provider video id when available
- building the embed URL
- providing a thumbnail when the source allows it
- declaring how playback should happen (iframe / html5)
"""
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.models.video import VideoSourceType


@dataclass
class ProviderResult:
    """Unified result of analyzing a video URL."""

    source_type: VideoSourceType | None = None
    valid: bool = False
    video_id: str | None = None
    embed_url: str | None = None
    thumbnail_url: str | None = None
    playable_mode: str = "unknown"  # "iframe" | "html5"
    message: str = ""
    canonical_url: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class BaseProvider:
    """Contract every concrete provider must implement."""

    name: ClassVar[str] = "base"
    source_type: ClassVar[VideoSourceType]
    PATTERNS: ClassVar[list[re.Pattern[str]]] = []

    def detect(self, url: str) -> re.Match[str] | None:
        """Return the first regex match if this URL belongs to this provider."""
        for pattern in self.PATTERNS:
            m = pattern.match(url.strip())
            if m:
                return m
        return None

    def analyze(self, url: str, match: re.Match[str]) -> ProviderResult:
        raise NotImplementedError


class NonEmbeddableError(Exception):
    """Raised when a source explicitly refuses embedding."""
