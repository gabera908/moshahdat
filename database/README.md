# Database

Schema is managed by **Alembic** in `backend/alembic/`.

```bash
cd backend
alembic upgrade head          # apply all migrations
alembic revision --autogenerate -m "change"   # create a new migration
alembic downgrade -1          # rollback last migration
```

Initial schema (revision `0001`):

users · categories · tags · videos · video_tags · playlists ·
playlist_videos · video_views · audit_logs

Seed data:

```bash
python -m scripts.seed            # admin user from env vars (idempotent)
python -m scripts.seed --demo     # demo categories/videos/playlist
python -m scripts.seed --init-tables --demo   # dev shortcut with SQLite/create_all
```
