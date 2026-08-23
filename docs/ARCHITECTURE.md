# Architecture Overview

```text
                    ┌─────────────────────┐
                    │   Nginx :8080         │
                    │  /  → frontend:3000 │
                    │  /api → backend:8000│
                    └──────────┬──────────┘
              ┌────────────────┼────────────────┐
              ▼                                 ▼
    ┌──────────────────┐             ┌──────────────────┐
    │ Next.js (SSR)    │             │ FastAPI          │
    │ Public website   │◄──REST──────│ /api/v1/*        │
    │ RTL · SEO        │             │ JWT · RBAC       │
    └──────────────────┘             │ Rate limit       │
                                     └────────┬─────────┘
                                              │ SQLAlchemy + Alembic
              ┌───────────────────┐           ▼
              │ PySide6 Desktop   │   ┌──────────────┐
              │ Admin (Windows)   ├──►│ PostgreSQL   │
              │ Dashboard · CRUD  │   └──────────────┘
              └───────────────────┘
```

## Backend layers

- `app/providers/` — VideoProvider abstraction. Each source implements
  `detect(url) -> match` and `analyze(url, match) -> ProviderResult`
  (embed URL, thumbnail, playback mode). Registry order matters; generic
  EmbedProvider is the catch-all fallback.
- `app/models/` — SQLAlchemy 2.0 typed models. BigInteger PKs use a
  SQLite-compatible variant so tests run without Postgres.
- `app/api/v1/` — routers grouped per resource with a shared deps module for
  auth/RBAC/pagination. Unified envelope on every response.
- `app/services/` — cross-cutting logic: slugs (Arabic-aware uniqueness),
  audit logging, view tracking (session dedupe + hashed IPs).

## Frontend conventions

- App Router server components fetch directly from `NEXT_PUBLIC_API_URL`.
- Interactive islands (search autocomplete, theme toggle, share buttons,
  view tracker) are client components using TanStack Query where needed.
- All UI strings live in `src/lib/i18n/ar.ts` to allow future English LTR.
- Theme: class-based dark mode, default dark, persisted in localStorage.

## Desktop app

- `api_client.py` — thread-safe httpx client + QThread workers; the GUI never
  blocks. Token refresh happens transparently on 401 once.
- Views are stacked widgets behind a sidebar; each exposes `on_show()` /
  `refresh()`. Errors surface as Arabic toasts; details go to a rotating log
  file under `%APPDATA%/VideoPlatformAdmin/logs`.

## Database schema

users · categories · videos · video_tags · tags · playlists ·
playlist_videos · video_views · audit_logs

Key indexes: `(status, created_at)` and `(category_id, status)` on videos,
`(video_id, viewed_at)` on video_views, unique slugs everywhere.

Soft delete: `videos.deleted_at` — public queries always filter it;
hard delete is admin-only via `?hard=true`.
