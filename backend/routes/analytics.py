"""
backend/routes/analytics.py

POST /analytics/events — ingest user-facing analytics events into Supabase.
"""

from fastapi import APIRouter

from backend import deps
from backend.constants import ANALYTICS_EVENT_TYPES

router = APIRouter(tags=["analytics"])


@router.post("/analytics/events", status_code=202)
async def analytics_event_ingest(payload: dict):
    event_type = str(payload.get("event_type") or "").strip()
    if event_type not in ANALYTICS_EVENT_TYPES:
        return {"accepted": False, "reason": "unsupported_event"}

    session_id = str(payload.get("session_id") or "").strip()[:128] or None
    manga_title = str(payload.get("manga_title") or "").strip()[:250] or None
    genre = str(payload.get("genre") or "").strip()[:100] or None

    # Accept user_id from authenticated clients (validated as UUID format)
    import re
    raw_user_id = str(payload.get("user_id") or "").strip()[:64] or None
    user_id = None
    if raw_user_id and re.match(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        raw_user_id, re.I,
    ):
        user_id = raw_user_id

    filter_state = payload.get("filter_state")
    if not isinstance(filter_state, dict):
        filter_state = None

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = None

    body = {
        "event_type": event_type,
        "session_id": session_id,
        "user_id": user_id,
        "manga_title": manga_title,
        "genre": genre,
        "filter_state": filter_state,
        "metadata": metadata,
    }

    try:
        r = await deps.sb_post("events", body)
    except Exception:
        return {"accepted": False, "reason": "network_error"}

    if r.status_code not in (200, 201):
        return {"accepted": False, "reason": "storage_error"}

    return {"accepted": True}
