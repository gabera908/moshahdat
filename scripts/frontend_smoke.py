"""Frontend rendering smoke test against running Next.js + FastAPI."""
import sys
import urllib.parse

import httpx

ok = fail = 0


def check(name, cond):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name)
    ok, fail = ok + (1 if cond else 0), fail + (0 if cond else 1)


c = httpx.Client(timeout=30)

home = c.get("http://localhost:3000/").text
check("home 200 + hero title", "منصة الفيديو" in home)
check('home dir="rtl"', 'dir="rtl"' in home)
check("home latest section", "أحدث الفيديوهات" in home)
check("home most viewed section", "الأكثر مشاهدة" in home)
check("dark theme default script", "localStorage" in home)

search = c.get("http://localhost:3000/search", params={"q": "MP4"}).text
check("search page renders", "نتائج البحث" in search)

cats = c.get("http://localhost:3000/categories").text
check("categories page", "التصنيفات" in cats and "وثائقي" in cats)

pls = c.get("http://localhost:3000/playlists").text
check("playlists page lists seeded", "أفضل اللحظات" in pls)

api = httpx.get("http://localhost:8000/api/v1/videos?page_size=1&sort=views").json()
slug = api["data"]["items"][0]["slug"]
page = c.get(f"http://localhost:3000/video/{urllib.parse.quote(slug)}").text
check("video detail page renders", "مشاهدة" in page)
check("video page JSON-LD VideoObject", "VideoObject" in page)
check("video OG meta", "og:title" in page or 'property="og' in page)
check("canonical link", "canonical" in page)

cat_page = c.get(
    "http://localhost:3000/categories/" + urllib.parse.quote("وثائقي")
).text
check("category videos page", "لا توجد فيديوهات" in cat_page or "التالي" in cat_page or "التصنيف" in cat_page)

sm = c.get("http://localhost:3000/sitemap.xml").text
check("sitemap includes video urls", "/video/" in sm)

rb = c.get("http://localhost:3000/robots.txt").text
check("robots.txt references sitemap", "sitemap.xml" in rb)

nf = c.get("http://localhost:3000/video/does-not-exist-xyz")
check("404 for missing video", nf.status_code == 404)

print(f"\n===== FRONTEND SMOKE: {ok} passed, {fail} failed =====")
sys.exit(1 if fail else 0)
