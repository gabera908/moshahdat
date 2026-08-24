"""Provider registry and public detection API."""
import logging
import re
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
        if provider.name == "gdrive" and result.video_id:
            # Full Drive pipeline: accessibility -> metadata -> thumbnail -> playback
            _gdrive_enrich(result)
        else:
            ok, detail = _probe(url)
            if not ok:
                logger.info("URL probe failed (%s): %s", url, detail)
                # A dead link is a warning, not a hard failure — sources may block bots.
                if detail == "unreachable":
                    result.message += " (تنبيه: تعذر الوصول للرابط الآن؛ قد يحجبه المصدر.)"

    return result


# --------------------------------------------------------------------------
# Google Drive pipeline (plan: فحص الوصول -> بيانات الملف -> اختبار التشغيل)
# --------------------------------------------------------------------------

_GDRIVE_UA = {"User-Agent": "Mozilla/5.0 (compatible; VideoPlatformBot/1.0)"}
_GDRIVE_STREAM = "https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
_GDRIVE_THUMB = "https://drive.google.com/thumbnail?id={fid}&sz=w640"


def _gdrive_fetch(file_id: str) -> dict:
    """Probe Google Drive for a file. Returns a plain dict (easy to mock):

    accessible     — the direct stream endpoint serves the media (public file)
    suggested_title— filename parsed from the view page (when public)
    thumbnail_ok   — the public thumbnail endpoint returned an image
    stream_ok      — stream answered 200 with a media content-type

    The stream endpoint is the source of truth for accessibility: the view
    page always contains a sign-in link, even for public files.
    """
    info: dict = {"accessible": False, "suggested_title": None,
                  "thumbnail_ok": False, "stream_ok": False}
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=_GDRIVE_UA) as client:
            # 1) Accessibility oracle: headers-only probe of the stream endpoint.
            try:
                req = client.build_request(
                    "GET", _GDRIVE_STREAM.format(fid=file_id)
                )
                with client.stream("GET", req.url) as stream:
                    ctype = stream.headers.get("content-type", "")
                    if stream.status_code in (401, 403):
                        return info  # definitively private
                    if stream.status_code == 200 and not ctype.startswith("text/html"):
                        info["accessible"] = True
                        info["stream_ok"] = True
                    elif stream.status_code == 200:
                        # Virus-scan interstitial or similar HTML — file is public
                        # but direct streaming is uncertain; preview iframe will play.
                        info["accessible"] = True
            except httpx.HTTPError:
                # Cannot reach Google at all: don't hard-fail, preview may still work.
                info["accessible"] = True
                return info

            # 2) Filename from the view page (public pages embed the real name).
            try:
                view = client.get(f"https://drive.google.com/file/d/{file_id}/view")
                m = re.search(r"<title>([^<]+)</title>", view.text or "", re.I)
                if m:
                    name = m.group(1).strip()
                    for suffix in (" - Google Drive", "– Google Drive"):
                        if name.endswith(suffix):
                            name = name[: -len(suffix)].strip()
                    if name and "Google Drive" not in name:
                        info["suggested_title"] = name
            except httpx.HTTPError:
                pass

            # 3) Public thumbnail (headers-only).
            try:
                treq = client.build_request("GET", _GDRIVE_THUMB.format(fid=file_id))
                with client.stream("GET", treq.url) as thumb:
                    info["thumbnail_ok"] = (
                        thumb.status_code == 200
                        and thumb.headers.get("content-type", "").startswith("image/")
                    )
            except httpx.HTTPError:
                pass
    except httpx.HTTPError:
        pass
    return info


def _gdrive_enrich(result: ProviderResult) -> None:
    """Run the full Drive pipeline and mutate `result` in place."""
    import httpx as _httpx

    fid = result.video_id or ""
    try:
        info = _gdrive_fetch(fid)
    except _httpx.HTTPError:
        # Network is down — keep the URL valid, playback verified later.
        result.message += " (تعذر التحقق الآن من إمكانية الوصول؛ تأكد من المشاركة «أي شخص لديه الرابط».)"
        return
    info = info if isinstance(info, dict) else {}

    if not info["accessible"]:
        result.valid = False
        result.playable_mode = "none"
        result.message = (
            "هذا الملف غير متاح للعموم على Google Drive ✗\n"
            "الحل: افتح الملف ← مشاركة ← غيّرها إلى «أي شخص لديه الرابط» ثم أعد فحص الرابط."
        )
        return

    if info["suggested_title"]:
        result.extras["suggested_title"] = info["suggested_title"]

    if info["thumbnail_ok"]:
        result.thumbnail_url = _GDRIVE_THUMB.format(fid=fid)

    if info["stream_ok"]:
        # Best experience: native HTML5 streaming straight from Google's CDN.
        result.playable_mode = "html5"
        result.extras["stream_url"] = _GDRIVE_STREAM.format(fid=fid)
        result.message = (
            "تم التحقق من ملف Google Drive ✓ — الملف متاح ويُشغّل مباشرة داخل الموقع "
            "(مشغل مدمج مع صورة مصغرة تلقائية)."
        )
    else:
        result.playable_mode = "iframe"
        result.message = (
            "الملف متاح وسيُشغّل عبر معاينة Google Drive داخل الموقع ✓ "
            "(تأكد من المشاركة «أي شخص لديه الرابط» لضمان التشغيل للزوار)."
        )


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
