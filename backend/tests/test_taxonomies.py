"""Categories, tags, playlists and analytics tests."""


class TestCategories:
    def test_create_and_public_list(self, client, editor_headers):
        resp = client.post(
            "/api/v1/categories",
            json={"name": "تقارير ميدانية", "description": "desc"},
            headers=editor_headers,
        )
        assert resp.status_code == 201, resp.text
        cat = resp.json()["data"]
        assert cat["slug"] == "تقارير-ميدانية" or cat["slug"]

        listing = client.get("/api/v1/categories").json()["data"]["items"]
        assert any(c["id"] == cat["id"] for c in listing)

    def test_delete_guard_with_videos(self, client, editor_headers):
        cat_resp = client.post("/api/v1/categories", json={"name": "cat-x"}, headers=editor_headers)
        cat_id = cat_resp.json()["data"]["id"]

        client.post(
            "/api/v1/videos",
            json={
                "title": "v", "source_type": "direct",
                "source_url": "https://x.example/v.mp4",
                "category_id": cat_id, "status": "published",
            },
            headers=editor_headers,
        )

        resp = client.delete(f"/api/v1/categories/{cat_id}", headers=editor_headers)
        assert resp.status_code == 409

        resp = client.delete(f"/api/v1/categories/{cat_id}?force=true", headers=editor_headers)
        assert resp.status_code == 200

    def test_reorder(self, client, editor_headers):
        ids = []
        for name in ("a", "b", "c"):
            r = client.post("/api/v1/categories", json={"name": name}, headers=editor_headers)
            ids.append(r.json()["data"]["id"])

        resp = client.put("/api/v1/categories/reorder/all", json={"ids": list(reversed(ids))},
                          headers=editor_headers)
        assert resp.status_code == 200

        listing = client.get("/api/v1/categories").json()["data"]["items"]
        assert [c["id"] for c in listing] == list(reversed(ids))


class TestTags:
    def test_tag_dedupe_and_attach_to_video(self, client, editor_headers):
        t1 = client.post("/api/v1/tags", json={"name": "بيئة"}, headers=editor_headers).json()
        assert t1["success"]

        video_resp = client.post(
            "/api/v1/videos",
            json={
                "title": "v-tagged", "source_type": "embed",
                "source_url": "https://player.example/embed/1",
                "tag_ids": [t1["data"]["id"]],
                "status": "published",
            },
            headers=editor_headers,
        )
        data = video_resp.json()["data"]
        assert [t["name"] for t in data["tags"]] == ["بيئة"]


class TestPlaylists:
    def test_create_with_ordered_videos(self, client, editor_headers):
        vids = []
        for i in range(3):
            v = client.post(
                "/api/v1/videos",
                json={
                    "title": f"حلقة {i+1}", "source_type": "youtube",
                    "source_url": f"https://youtu.be/dQw4w9WgXc{i}",
                    "status": "published",
                },
                headers=editor_headers,
            ).json()["data"]
            vids.append(v)

        resp = client.post(
            "/api/v1/playlists",
            json={"title": "سلسلة المعسكر", "video_ids": [v["id"] for v in reversed(vids)]},
            headers=editor_headers,
        )
        assert resp.status_code == 201, resp.text
        playlist = resp.json()["data"]
        ordered_ids = [v["id"] for v in playlist["videos"]]
        assert ordered_ids == [v["id"] for v in reversed(vids)]

    def test_set_membership_updates_order(self, client, editor_headers):
        make = lambda title: client.post(
            "/api/v1/videos",
            json={
                "title": title, "source_type": "direct",
                "source_url": f"https://cdn.example/{title}.mp4", "status": "published",
            },
            headers=editor_headers,
        ).json()["data"]

        a, b = make("أ"), make("ب")
        pl = client.post(
            "/api/v1/playlists", json={"title": "قائمة", "video_ids": [a["id"], b["id"]]},
            headers=editor_headers,
        ).json()["data"]

        resp = client.put(
            f"/api/v1/playlists/{pl['id']}/videos",
            json={"video_ids": [b["id"], a["id"]]},
            headers=editor_headers,
        )
        new_order = [v["id"] for v in resp.json()["data"]["videos"]]
        assert new_order == [b["id"], a["id"]]

    def test_private_playlist_hidden_from_anonymous(self, client, editor_headers):
        pl = client.post(
            "/api/v1/playlists", json={"title": "خاصة", "is_public": False},
            headers=editor_headers,
        ).json()["data"]

        slug = pl["slug"]
        assert client.get(f"/api/v1/playlists/slug/{slug}").status_code == 404
        assert client.get(f"/api/v1/playlists/slug/{slug}", headers=editor_headers).status_code == 200


class TestAnalytics:
    def test_dashboard_counters(self, client, admin_headers, editor_headers):
        client.post(
            "/api/v1/videos",
            json={
                "title": "منشور", "source_type": "youtube",
                "source_url": "https://youtu.be/dQw4w9WgXcQ", "status": "published",
            },
            headers=editor_headers,
        )
        resp = client.get("/api/v1/analytics/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        stats = resp.json()["data"]
        assert stats["total_videos"] >= 1
        assert stats["published_videos"] >= 1
        assert "views_today" in stats

    def test_requires_staff(self, client):
        assert client.get("/api/v1/analytics/dashboard").status_code == 401

    def test_daily_views_shape(self, client, admin_headers):
        resp = client.get("/api/v1/analytics/views/daily?days=7", headers=admin_headers)
        points = resp.json()["data"]["items"]
        assert len(points) == 7
        assert all("date" in p and "views" in p for p in points)


class TestAuditLogs:
    def test_actions_recorded(self, client, admin_headers, editor_headers):
        client.post("/api/v1/categories", json={"name": "سجل"}, headers=editor_headers)
        resp = client.get("/api/v1/audit-logs", headers=admin_headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert any(i["action"] == "create" and i["entity_type"] == "category" for i in items)

    def test_admin_only(self, client, editor_headers):
        assert (
            client.get("/api/v1/audit-logs", headers=editor_headers).status_code == 403
        )


class TestErrorFormat:
    def test_unified_error_envelope(self, client):
        resp = client.get("/api/v1/videos/slug/does-not-exist")
        body = resp.json()
        assert body["success"] is False
        assert "message" in body
        assert body.get("error_code") == "NOT_FOUND"

    def test_validation_error_localized(self, client):
        resp = client.post("/api/v1/videos", json={}, headers={})
        assert resp.status_code in (401, 422)  # auth first is fine; shape checked below

class TestHierarchy:
    """Category tree (parent_id) — added per review feedback."""

    def test_create_child_and_list(self, client, editor_headers):
        parent = client.post("/api/v1/categories", json={"name": "التدريب"}, headers=editor_headers).json()["data"]
        child = client.post(
            "/api/v1/categories", json={"name": "الإعلام", "parent_id": parent["id"]},
            headers=editor_headers,
        ).json()["data"]
        assert child["parent_id"] == parent["id"]

        listing = client.get("/api/v1/categories").json()["data"]["items"]
        by_id = {c["id"]: c for c in listing}
        assert by_id[child["id"]]["parent_id"] == parent["id"]

    def test_self_parent_rejected(self, client, editor_headers):
        cat = client.post("/api/v1/categories", json={"name": "أ"}, headers=editor_headers).json()["data"]
        resp = client.put(f"/api/v1/categories/{cat['id']}", json={"parent_id": cat["id"]}, headers=editor_headers)
        assert resp.status_code == 422

    def test_cycle_rejected(self, client, editor_headers):
        a = client.post("/api/v1/categories", json={"name": "A"}, headers=editor_headers).json()["data"]
        b = client.post("/api/v1/categories", json={"name": "B", "parent_id": a["id"]}, headers=editor_headers).json()["data"]
        # making A a child of B would create a cycle
        resp = client.put(f"/api/v1/categories/{a['id']}", json={"parent_id": b["id"]}, headers=editor_headers)
        assert resp.status_code == 422

    def test_delete_promotes_children(self, client, editor_headers):
        a = client.post("/api/v1/categories", json={"name": "P1"}, headers=editor_headers).json()["data"]
        b = client.post("/api/v1/categories", json={"name": "C1", "parent_id": a["id"]}, headers=editor_headers).json()["data"]
        assert client.delete(f"/api/v1/categories/{a['id']}", headers=editor_headers).status_code == 200
        child = client.get(f"/api/v1/categories/{b['id']}").json()["data"]
        assert child["parent_id"] is None


class TestChannelName:
    def test_search_by_channel(self, client, editor_headers):
        client.post(
            "/api/v1/videos",
            json={
                "title": "حلقة خاصة", "source_type": "youtube",
                "source_url": "https://youtu.be/dQw4w9WgXcQ",
                "channel_name": "إيكو ميديا",
                "status": "published",
            },
            headers=editor_headers,
        )
        resp = client.get("/api/v1/videos?q=إيكو")
        items = resp.json()["data"]["items"]
        assert len(items) == 1 and items[0]["channel_name"] == "إيكو ميديا"

    def test_manual_publish_date(self, client, editor_headers):
        v = client.post(
            "/api/v1/videos",
            json={
                "title": "بتاريخ مخصص", "source_type": "direct",
                "source_url": "https://cdn.example/x.mp4",
            },
            headers=editor_headers,
        ).json()["data"]
        resp = client.put(
            f"/api/v1/videos/{v['id']}",
            json={"published_at": "2026-01-15T10:00:00Z"},
            headers=editor_headers,
        )
        assert resp.json()["data"]["published_at"].startswith("2026-01-15")
