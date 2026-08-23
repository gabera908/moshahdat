"""Videos CRUD, publishing and view tracking tests."""
from datetime import datetime, timezone


def _create_video(client, headers, title="فيديو تجريبي", status="draft", **overrides):
    payload = {
        "title": title,
        "description": "وصف الفيديو",
        "source_type": "youtube",
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "status": status,
        **overrides,
    }
    resp = client.post("/api/v1/videos", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


class TestCrud:
    def test_create_fills_embed_and_thumbnail(self, client, editor_headers):
        video = _create_video(client, editor_headers)
        assert video["slug"]
        assert "/embed/" in (video["embed_url"] or "")
        assert video["thumbnail_url"]

    def test_create_requires_auth(self, client):
        payload = {
            "title": "x", "source_type": "youtube",
            "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        }
        assert client.post("/api/v1/videos", json=payload).status_code == 401

    def test_update_changes_slug(self, client, editor_headers):
        video = _create_video(client, editor_headers, title="عنوان أول")
        resp = client.put(
            f"/api/v1/videos/{video['id']}",
            json={"title": "عنوان جديد تمامًا"},
            headers=editor_headers,
        )
        assert resp.status_code == 200
        updated = resp.json()["data"]
        assert updated["title"] == "عنوان جديد تمامًا"
        assert updated["slug"] != video["slug"]

    def test_soft_delete_then_hard_delete(self, client, admin_headers, editor_headers):
        video = _create_video(client, editor_headers)

        # Editor can soft delete
        assert client.delete(f"/api/v1/videos/{video['id']}", headers=editor_headers).status_code == 200

        # Hard delete is admin-only
        assert (
            client.delete(f"/api/v1/videos/{video['id']}?hard=true", headers=editor_headers).status_code
            == 403
        )
        assert (
            client.delete(f"/api/v1/videos/{video['id']}?hard=true", headers=admin_headers).status_code
            == 200
        )


class TestLifecycle:
    def test_publish_then_visible_publicly(self, client, editor_headers, category):
        video = _create_video(client, editor_headers, category_id=category.id)

        slug = video["slug"]
        assert client.get(f"/api/v1/videos/slug/{slug}").status_code == 404  # draft hidden

        assert client.post(f"/api/v1/videos/{video['id']}/publish", headers=editor_headers).status_code == 200
        resp = client.get(f"/api/v1/videos/slug/{slug}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["published_at"] is not None

    def test_moderator_can_publish_but_not_edit(self, client, editor_headers, moderator_setup):
        headers = moderator_setup
        video = _create_video(client, editor_headers)
        assert client.post(f"/api/v1/videos/{video['id']}/publish", headers=headers).status_code == 200

        resp = client.put(
            f"/api/v1/videos/{video['id']}", json={"title": "hack"}, headers=headers
        )
        assert resp.status_code == 403

    def test_archive(self, client, editor_headers):
        video = _create_video(client, editor_headers)
        assert client.post(f"/api/v1/videos/{video['id']}/archive", headers=editor_headers).status_code == 200
        detail = client.get(f"/api/v1/videos/{video['id']}", headers=editor_headers).json()["data"]
        assert detail["status"] == "archived"

    def test_duplicate_creates_draft(self, client, editor_headers):
        video = _create_video(client, editor_headers, status="published")
        resp = client.post(f"/api/v1/videos/{video['id']}/duplicate", headers=editor_headers)
        assert resp.status_code == 201
        clone = resp.json()["data"]
        assert clone["id"] != video["id"]
        assert clone["status"] == "draft"
        assert "(نسخة)" in clone["title"]


class TestListing:
    def test_public_listing_only_published(self, client, editor_headers, db):
        _create_video(client, editor_headers, title="مسودة")
        published = _create_video(client, editor_headers, title="منشور", status="published")

        resp = client.get("/api/v1/videos")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        titles = [i["title"] for i in items]
        assert "منشور" in titles
        assert "مسودة" not in titles

    def test_search_filters(self, client, editor_headers):
        v1 = _create_video(client, editor_headers, title="افتتاح المعسكر الصيفي", status="published")
        _create_video(client, editor_headers, title="درس البرمجة", status="published")

        resp = client.get("/api/v1/videos?q=المعسكر")
        titles = [i["title"] for i in resp.json()["data"]["items"]]
        assert len(titles) == 1
        assert "المعسكر" in titles[0]

    def test_pagination_meta(self, client, editor_headers):
        for i in range(5):
            _create_video(client, editor_headers, title=f"فيديو {i}", status="published")

        body = client.get("/api/v1/videos?page_size=2&page=2").json()
        meta = body["data"]["meta"]
        assert meta["total"] == 5
        assert meta["pages"] == 3
        assert meta["page"] == 2
        assert len(body["data"]["items"]) == 2


class TestViews:
    def test_view_counted_once_per_session(self, client, editor_headers):
        video = _create_video(client, editor_headers, status="published")

        for _ in range(3):
            resp = client.post(
                f"/api/v1/videos/{video['id']}/view",
                json={"session_id": "session-abc123"},
                headers={"user-agent": "pytest/1.0"},
            )
            assert resp.status_code == 200

        detail = client.get(f"/api/v1/videos/slug/{video['slug']}").json()["data"]
        assert detail["views_count"] == 1  # deduped by session within the window


class TestBulk:
    def test_bulk_publish(self, client, editor_headers):
        ids = [
            _create_video(client, editor_headers, title=f"v{i}")["id"] for i in range(3)
        ]
        resp = client.post(
            "/api/v1/videos/bulk", json={"action": "publish", "ids": ids}, headers=editor_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["affected"] == 3

        for vid in ids:
            detail = client.get(f"/api/v1/videos/{vid}", headers=editor_headers).json()["data"]
            assert detail["status"] == "published"
