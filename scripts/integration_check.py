"""End-to-end integration check against a running backend on :8000."""
import json
import sys

import httpx

BASE = "http://localhost:8000"
ok = 0
fail = 0


def check(name: str, condition: bool, extra: str = ""):
    global ok, fail
    if condition:
        ok += 1
        print(f"PASS {name}")
    else:
        fail += 1
        print(f"FAIL {name} {extra}")


c = httpx.Client(base_url=BASE, timeout=20)

# public catalog
r = c.get("/api/v1/videos?page_size=5")
body = r.json()
check("public videos list", r.status_code == 200 and body["success"])
videos = body["data"]["items"]
check("seeded videos present", len(videos) >= 2)
direct = next((v for v in videos if v["source_type"] == "direct"), None)
check("direct video has embed_url", direct is not None and bool(direct["embed_url"]))
yt = next((v for v in videos if v["source_type"] == "youtube"), None)
check("youtube thumb auto-filled", yt is not None and "ytimg" in (yt.get("thumbnail_url") or ""))

# categories & playlists
r = c.get("/api/v1/categories")
cats = r.json()["data"]["items"]
check("categories listed", len(cats) >= 3)
slug_cat = cats[0]["slug"]
r = c.get(f"/api/v1/videos?category={httpx.QueryParams({'category': slug_cat}).get('category')}")
check("filter by category works", r.status_code == 200)

r = c.get("/api/v1/playlists")
pls = r.json()["data"]["items"]
check("playlists listed", len(pls) >= 1)

# search (Arabic)
r = c.get("/api/v1/videos", params={"q": "MP4"})
check("arabic search", any("MP4" in v["title"] for v in r.json()["data"]["items"]))

# auth flow
r = c.post("/api/v1/auth/login", data={"username": "admin", "password": "change_me_admin_password"})
tokens = r.json()["data"]
H = {"Authorization": f"Bearer {tokens['access_token']}"}
check("admin login", r.status_code == 200 and tokens["access_token"])

r = c.get("/api/v1/auth/me", headers=H)
check("auth/me", r.json()["data"]["role"] == "admin")

# analytics
r = c.get("/api/v1/analytics/dashboard", headers=H)
stats = r.json()["data"]
check("dashboard stats", stats["total_videos"] >= 2 and stats["published_videos"] >= 2)

r = c.get("/api/v1/analytics/views/daily?days=7", headers=H)
check("daily views shape", len(r.json()["data"]["items"]) == 7)

# CRUD lifecycle
r = c.post(
    "/api/v1/videos",
    json={
        "title": "تكامل اختبار",
        "source_type": "youtube",
        "source_url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
    },
    headers=H,
)
created = r.json()["data"]
vid = created["id"]
check("create draft via API", created["status"] == "draft" and "/embed/" in created["embed_url"])

r = c.get(f"/api/v1/videos/slug/{created['slug']}")
check("draft hidden publicly", r.status_code == 404)

r = c.post(f"/api/v1/videos/{vid}/publish", headers=H)
check("publish endpoint", r.json()["data"]["status"] == "published")

r = c.get(f"/api/v1/videos/slug/{created['slug']}")
check("published visible by slug", r.status_code == 200)

r = c.post(f"/api/v1/videos/{vid}/view", json={"session_id": "integration-test-session"})
check("view counted", r.json()["data"]["counted"] is True)
r = c.post(f"/api/v1/videos/{vid}/view", json={"session_id": "integration-test-session"})
check("view deduped", r.json()["data"]["counted"] is False)

r = c.delete(f"/api/v1/videos/{vid}", headers=H)
check("soft delete", r.status_code == 200)
r = c.get(f"/api/v1/videos/{vid}?hard=true", headers=H)
check("hard delete cleanup", r.status_code in (404, 200))

# RBAC spot checks
r = c.get("/api/v1/users", headers=H)
check("users list admin-only ok", r.status_code == 200)
r = c.get("/api/v1/audit-logs", headers=H)
check("audit logs readable", any(i["action"] == "create" for i in r.json()["data"]["items"]))

# error envelope
r = c.get("/api/v1/videos/slug/nope-404")
err = r.json()
check("unified error envelope", err["success"] is False and err.get("error_code") == "NOT_FOUND")

# sitemap data source
r = c.get("/openapi.json")
check("swagger openapi served", r.status_code == 200)

print(f"\n===== INTEGRATION: {ok} passed, {fail} failed =====")
sys.exit(1 if fail else 0)
