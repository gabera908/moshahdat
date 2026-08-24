# -*- coding: utf-8 -*-
"""Headers-only probe of the user's Drive file (never downloads the video)."""
import re

import httpx

fid = "1h3-1egW4qjDhNpEY9tr479hBSqLzagI_"
h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

with httpx.Client(timeout=20, follow_redirects=True, headers=h) as c:
    v = c.get(f"https://drive.google.com/file/d/{fid}/view")
    title = re.search(r"<title>([^<]+)</title>", v.text or "")
    print("view status   :", v.status_code)
    print("title         :", (title.group(1) if title else "NONE")[:80])
    print("Access denied :", "Access denied" in (v.text or ""))
    print("ServiceLogin  :", "accounts.google.com/ServiceLogin" in (v.text or ""))

    with c.stream(
        "GET",
        f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t",
    ) as u:
        print("stream status :", u.status_code, "|", u.headers.get("content-type"))
