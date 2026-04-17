"""
backend/routes/feedback.py

POST /feedback — send user feedback to support email via Resend.
"""

from __future__ import annotations

import os
import re
from html import escape
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from backend import deps

router = APIRouter(tags=["feedback"])

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class FeedbackPayload(BaseModel):
    feedback_type: Literal["bug", "suggestion", "general"] = "general"
    message: str = Field(..., min_length=8, max_length=2000)
    email: str | None = Field(default=None, max_length=200)
    page: str | None = Field(default=None, max_length=400)
    website: str | None = Field(default="", max_length=200)  # honeypot field

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 8:
            raise ValueError("Message is too short.")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not EMAIL_RE.match(cleaned):
            raise ValueError("Email format is invalid.")
        return cleaned

    @field_validator("page")
    @classmethod
    def validate_page(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


def _feedback_env() -> tuple[str, str, str]:
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    from_email = (os.getenv("FEEDBACK_FROM_EMAIL") or "").strip()
    to_email = (os.getenv("FEEDBACK_TO_EMAIL") or "").strip()
    return api_key, from_email, to_email


def _build_text_body(payload: FeedbackPayload, request: Request) -> str:
    request_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    lines = [
        f"Type: {payload.feedback_type}",
        f"Reply email: {payload.email or 'not provided'}",
        f"Page: {payload.page or 'not provided'}",
        f"IP: {request_ip}",
        f"User-Agent: {user_agent}",
        "",
        "Message:",
        payload.message,
    ]
    return "\n".join(lines)


def _build_html_body(payload: FeedbackPayload, request: Request) -> str:
    request_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    msg_html = "<br>".join(escape(payload.message).splitlines())
    return (
        "<h2>New ManhwaRank Feedback</h2>"
        f"<p><strong>Type:</strong> {escape(payload.feedback_type)}</p>"
        f"<p><strong>Reply email:</strong> {escape(payload.email or 'not provided')}</p>"
        f"<p><strong>Page:</strong> {escape(payload.page or 'not provided')}</p>"
        f"<p><strong>IP:</strong> {escape(request_ip)}</p>"
        f"<p><strong>User-Agent:</strong> {escape(user_agent)}</p>"
        f"<hr><p>{msg_html}</p>"
    )


@router.post("/feedback", status_code=202)
@deps.limiter.limit("8/hour")
async def submit_feedback(request: Request, payload: FeedbackPayload):
    # Silently accept honeypot submissions to avoid signaling bot detection.
    if payload.website and payload.website.strip():
        return {"accepted": True}

    api_key, from_email, to_email = _feedback_env()
    if not api_key or not from_email or not to_email:
        raise HTTPException(status_code=503, detail="Feedback service is not configured.")

    if deps.http_client is None:
        raise HTTPException(status_code=503, detail="Feedback service is not available.")

    body = {
        "from": from_email,
        "to": [to_email],
        "subject": f"[ManhwaRank] {payload.feedback_type.title()} feedback",
        "text": _build_text_body(payload, request),
        "html": _build_html_body(payload, request),
    }

    if payload.email:
        body["reply_to"] = [payload.email]

    try:
        response = await deps.http_client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to send feedback.")

    if response.status_code not in (200, 202):
        raise HTTPException(status_code=502, detail="Feedback provider rejected the request.")

    return {"accepted": True}
