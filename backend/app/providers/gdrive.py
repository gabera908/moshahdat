"""Google Drive provider (public shareable files only)."""
import re
from typing import ClassVar

from app.models.video import VideoSourceType
from app.providers.base import BaseProvider, ProviderResult


class GoogleDriveProvider(BaseProvider):
    name = "gdrive"
    source_type = VideoSourceType.GDRIVE
    PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^(?:https?://)?(?:www\.)?drive\.google\.com/file/d/([A-Za-z0-9_-]{20,})(?:/[^?#]*)?(?:\?.*)?$", re.I),
        re.compile(r"^(?:https?://)?drive\.google\.com/open\?id=([A-Za-z0-9_-]{20,})$", re.I),
        re.compile(r"^(?:https?://)?drive\.google\.com/uc\?.*id=([A-Za-z0-9_-]{20,}).*$", re.I),
    ]

    def analyze(self, url: str, match: re.Match[str]) -> ProviderResult:
        file_id = match.group(1)
        return ProviderResult(
            source_type=self.source_type,
            valid=True,
            video_id=file_id,
            embed_url=f"https://drive.google.com/file/d/{file_id}/preview",
            thumbnail_url=None,
            playable_mode="iframe",
            message=(
                "تم التعرف على ملف Google Drive. تأكد أن مشاركة الملف "
                "\"أي شخص لديه الرابط\" وإلا لن يعمل التشغيل داخل الموقع."
            ),
            extras={"canonical": f"https://drive.google.com/file/d/{file_id}/view"},
        )
