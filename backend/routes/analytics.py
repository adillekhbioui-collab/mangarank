"""
backend/routes/analytics.py

POST /analytics/events — ingest user-facing analytics events into Supabase.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from backend import deps
from backend.constants import ANALYTICS_EVENT_TYPES

router = APIRouter(tags=["analytics"])


class AnalyticsPayload(BaseModel):
    event_type: str = Field(..., max_length=50)
    session_id: Optional[str] = Field(None, max_length=128)
    user_id: Optional[str] = Field(
        None, 
        pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    )
    manga_title: Optional[str] = Field(None, max_length=250)
    genre: Optional[str] = Field(None, max_length=100)
    filter_state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/analytics/events", status_code=202)
@deps.limiter.limit("60/minute")
async def analytics_event_ingest(request: Request, payload: AnalyticsPayload):
    if payload.event_type not in ANALYTICS_EVENT_TYPES:
        return {"accepted": False, "reason": "unsupported_event"}

    body = payload.model_dump()

    try:
        r = await deps.sb_post("events", body)
    except Exception:
        return {"accepted": False, "reason": "network_error"}

    if r.status_code not in (200, 201):
        return {"accepted": False, "reason": "storage_error"}

    return {"accepted": True}
