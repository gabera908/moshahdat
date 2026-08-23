"""Aggregated v1 API router."""
from fastapi import APIRouter

from app.api.v1 import analytics, audit_logs, auth, categories, playlists, tags, users, videos

api_router = APIRouter()

for module_router in (
    auth.router,
    videos.router,
    categories.router,
    tags.router,
    playlists.router,
    users.router,
    analytics.router,
    audit_logs.router,
):
    api_router.include_router(module_router)


@api_router.get("/providers", tags=["providers"])
def list_providers() -> dict:
    """Available video source providers for admin UIs."""
    from app.providers import PROVIDER_LABELS

    items = [
        {"key": key, "label": label}
        for key, label in PROVIDER_LABELS.items()
    ]
    return {"success": True, "message": "", "data": {"items": items}}
