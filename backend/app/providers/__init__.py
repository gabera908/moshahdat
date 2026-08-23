"""Provider registry and public detection API."""
import logging
from typing import NamedTuple

import httpx

from app.models.video import VideoSourceType
from app.providers.base import BaseProvider, NonEmbeddableError, ProviderResult
from app.providers.direct import DirectURLProvider
from app.providers.dropbox import DropboxProvider
from app.providers.embed import EmbedProvider
from app.providers.gdrive import GoogleDriveProvider
from app.providers.vimeo import VimeoProvider
from app.providers.youtube import YouTubeProvider

logger = logging.getLogger(__name__)


class ProviderInfo(NamedTuple):
    key: str
    label: str


# Ordered: specific providers first, generic embed LAST (catch-all).
PROVIDERS: list[BaseProvider] = [
    YouTubeProvider(),
    GoogleDriveProvider(),
    VimeoProvider(),
    DropboxProvider(),
    DirectURLProvider(),
    EmbedProvider(),
]

PROVIDER_LABELS: dict[str, str] = {
    "youtube": "YouTube",
    "gdrive": "Google Drive",
    "vimeo": "Vimeo",
    "dropbox": "Dropbox",
    "direct": "رابط مباشر",
    "embed": "Embed URL",
}


def detect_provider(url: str) -> tuple[BaseProvider | None, ProviderResult | None]:
    """Return the first provider whose pattern matches the URL."""
    for provider in PROVIDERS:
        m = provider.detect(url)
        if m:
            try:
                return provider, provider.analyze(url, m)
            except NonEmbeddableError as exc:
                return provider, ProviderResult(valid=False, message=str(exc))
    return None, None


def check_url(url: str, verify_reachable: bool = True) -> ProviderResult:
    """Analyze a video URL end-to-end.

    Steps: validate format -> detect provider -> build embed/thumbnail ->
    optionally verify reachability with a short HEAD/GET request.
    Never raises for network problems; failures are reported in `message`.
    """
    url = (url or "").strip()
    if not url:
        return ProviderResult(valid=False, message="الرجاء إدخال رابط الفيديو.")

    if not url.lower().startswith(("http://", "https://")):
        return ProviderResult(
            valid=False,
            message="الرابط غير صالح. يجب أن يبدأ بـ http:// أو https://",
        )

    provider, result = detect_provider(url)
    if provider is None or result is None or not result.valid:
        return ProviderResult(
            valid=False,
            message="تعذر التعرف على نوع الرابط. تأكد من صحته أو اختر مصدرًا يدويًا.",
        )

    if verify_reachable:
        ok, detail = _probe(url)
        if not ok:
            logger.info("URL probe failed (%s): %s", url, detail)
            # A dead link is a warning, not a hard failure — sources may block bots.
            if detail == "unreachable":
                result.message += " (تنبيه: تعذر الوصول للرابط الآن؛ قد يحجبه المصدر.)"

    return result


def _probe(url: str) -> tuple[bool, str]:
    """Best-effort reachability probe with a strict timeout."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; VideoPlatformBot/1.0)"}
    try:
        with httpx.Client(timeout=6.0, follow_redirects=True, headers=headers) as client:
            resp = client.head(url)
            if resp.status_code >= 400 or resp.status_code == 405:
                resp = client.get(url)
            if resp.status_code < 400:
                return True, "ok"
            return False, f"http_{resp.status_code}"
    except httpx.HTTPError:
        return False, "unreachable"


def list_providers() -> list[dict[str, str]]:
    """Providers exposed to admin UIs."""
    return [{"key": p.name, "label": PROVIDER_LABELS.get(p.name, p.name)} for p in PROVIDERS]


__all__ = [
    "BaseProvider",
    "ProviderResult",
    "VideoSourceType",
    "check_url",
    "detect_provider",
    "list_providers",
]
