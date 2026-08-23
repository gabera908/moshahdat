"""Unit tests for video URL providers."""
import pytest

from app.models.video import VideoSourceType
from app.providers import check_url, detect_provider
from app.providers.youtube import YouTubeProvider


class TestDetection:
    def test_youtube_watch(self):
        result = check_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ", verify_reachable=False)
        assert result.valid
        assert result.source_type == VideoSourceType.YOUTUBE
        assert result.video_id == "dQw4w9WgXcQ"
        assert "youtube.com/embed/dQw4w9WgXcQ" in (result.embed_url or "")

    def test_youtube_short_link(self):
        result = check_url("https://youtu.be/dQw4w9WgXcQ?t=42", verify_reachable=False)
        assert result.valid
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.thumbnail_url and "hqdefault" in result.thumbnail_url

    def test_youtube_shorts(self):
        provider, _ = detect_provider("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        assert isinstance(provider, YouTubeProvider)

    def test_gdrive_file(self):
        fid = "1A2b3C4d5E6f7G8h9I0jK1l2M3n4O5p6"
        result = check_url(f"https://drive.google.com/file/d/{fid}/view?usp=sharing", verify_reachable=False)
        assert result.valid
        assert result.source_type == VideoSourceType.GDRIVE
        assert f"/file/d/{fid}/preview" in result.embed_url

    def test_vimeo(self):
        result = check_url("https://vimeo.com/76979871", verify_reachable=False)
        assert result.valid
        assert result.embed_url == "https://player.vimeo.com/video/76979871"

    def test_dropbox_converts_dl_param(self):
        result = check_url(
            "https://www.dropbox.com/scl/fi/abc123/video.mp4?dl=0", verify_reachable=False
        )
        assert result.valid
        assert result.source_type == VideoSourceType.DROPBOX
        assert "raw=1" in result.embed_url
        assert result.playable_mode == "html5"

    def test_direct_mp4(self):
        url = "https://cdn.example.com/media/clip.mp4"
        result = check_url(url, verify_reachable=False)
        assert result.valid
        assert result.source_type == VideoSourceType.DIRECT
        assert result.playable_mode == "html5"
        assert result.embed_url == url

    def test_embed_fallback(self):
        result = check_url("https://some-site.example/player/xyz", verify_reachable=False)
        assert result.valid
        assert result.source_type == VideoSourceType.EMBED
        assert "iframe" in result.playable_mode or result.playable_mode == "iframe"

    def test_invalid_scheme(self):
        result = check_url("ftp://example.com/video.mp4", verify_reachable=False)
        assert not result.valid
        assert "http" in result.message

    def test_empty(self):
        result = check_url("", verify_reachable=False)
        assert not result.valid


@pytest.mark.parametrize("url", [
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtube.com/watch?v=dQw4w9WgXcQ&t=1s",
])
def test_youtube_variants(url):
    provider, result = detect_provider(url)
    assert isinstance(provider, YouTubeProvider)
    assert result.video_id == "dQw4w9WgXcQ"
