"""Google Drive full-pipeline tests (mocked network)."""
import pytest

from app.models.video import VideoSourceType
from app.providers import ProviderResult, check_url
from app.providers.gdrive import GoogleDriveProvider

FID = "1A2b3C4d5E6f7G8h9I0jK1l2M3n4O5p6"
URL = f"https://drive.google.com/file/d/{FID}/view?usp=sharing"


def _fake_fetch(**overrides):
    base = {
        "accessible": True,
        "suggested_title": "مقطع المعسكر.mp4",
        "thumbnail_ok": True,
        "stream_ok": True,
    }
    base.update(overrides)
    return base


@pytest.fixture()
def mock_public(monkeypatch):
    import app.providers as prov

    monkeypatch.setattr(prov, "_gdrive_fetch", lambda fid: _fake_fetch())
    return prov


class TestPipeline:
    def test_public_file_full_pipeline(self, mock_public):
        result = check_url(URL, verify_reachable=True)
        assert result.valid
        assert result.video_id == FID
        assert result.playable_mode == "html5"
        assert result.thumbnail_url and "thumbnail" in result.thumbnail_url
        assert result.extras["suggested_title"] == "مقطع المعسكر.mp4"
        assert result.extras["stream_url"].startswith("https://drive.usercontent.google.com")
        assert "✓" in result.message

    def test_private_file_rejected_with_guidance(self, mock_public, monkeypatch):
        import app.providers as prov

        monkey_private = lambda fid: _fake_fetch(accessible=False)  # noqa: E731
        monkeypatch.setattr(prov, "_gdrive_fetch", monkey_private)

        result = check_url(URL, verify_reachable=True)
        assert not result.valid
        assert "أي شخص لديه الرابط" in result.message

    def test_public_but_stream_down_falls_back_to_preview(self, mock_public, monkeypatch):
        import app.providers as prov

        monkeypatch.setattr(prov, "_gdrive_fetch", lambda fid: _fake_fetch(stream_ok=False))

        result = check_url(URL, verify_reachable=True)
        assert result.valid
        assert result.playable_mode == "iframe"
        assert "/preview" in result.embed_url

    def test_network_failure_stays_valid_with_warning(self, monkeypatch):
        import app.providers as prov

        monkeypatch.setattr(prov, "_gdrive_fetch", lambda fid: _fake_fetch(
            accessible=False, thumbnail_ok=False, stream_ok=False, suggested_title=None,
        ))
        # simulate total network failure via exception path
        def boom(fid):
            import httpx

            raise httpx.ConnectError("down")

        monkeypatch.setattr(prov, "_gdrive_fetch", boom)
        result = check_url(URL, verify_reachable=True)
        # network failure must not hard-fail the URL
        assert result.valid
        assert result.embed_url.endswith("/preview")

    def test_no_probe_when_verify_disabled(self):
        """create_video path: pure analysis, no network, still valid."""
        result = check_url(URL, verify_reachable=False)
        assert result.valid
        assert result.video_id == FID
        assert result.thumbnail_url is None  # only set after verification
        assert result.playable_mode == "iframe"

    def test_provider_detection_unchanged(self):
        from app.providers import detect_provider

        result = check_url(URL, verify_reachable=False)
        assert result.valid
        assert result.video_id == FID
        provider, detected = detect_provider(URL)
        assert isinstance(provider, GoogleDriveProvider)
        assert detected.source_type == VideoSourceType.GDRIVE
