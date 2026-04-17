"""
backend/main.py

FastAPI application bootstrap.
- Creates the app and configures CORS.
- Manages the shared async HTTP client lifecycle (lifespan).
- Includes all route modules via app.include_router().

All endpoint logic lives in backend/routes/*.

Run: uvicorn backend.main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import deps
from backend.routes import analytics, admin, feedback, manga, proxy


def _with_loopback_variants(origins: list[str]) -> list[str]:
    """Expand localhost/127.0.0.1 origins so either host works in dev."""
    expanded: set[str] = set()

    for origin in origins:
        normalized = origin.strip().rstrip("/")
        if not normalized:
            continue

        expanded.add(normalized)
        parsed = urlparse(normalized)

        if parsed.scheme and parsed.netloc:
            if parsed.hostname == "localhost":
                variant = normalized.replace("localhost", "127.0.0.1", 1)
                expanded.add(variant)
            elif parsed.hostname == "127.0.0.1":
                variant = normalized.replace("127.0.0.1", "localhost", 1)
                expanded.add(variant)

    return sorted(expanded)


def get_allowed_origins() -> list[str]:
    """Return normalized CORS origins from env or safe defaults."""
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    if raw:
        configured = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
        return _with_loopback_variants(configured)

    defaults = [
        "http://localhost:8000",
        "http://localhost:5173",
        "http://localhost:3000",
        "https://manhwa-rank.vercel.app",
    ]
    return _with_loopback_variants(defaults)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the shared async HTTP client at startup and close it on shutdown."""
    client = httpx.AsyncClient(timeout=15)
    deps.set_http_client(client)
    yield
    await client.aclose()


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# ── FastAPI app + CORS ─────────────────────────────────────────
app = FastAPI(
    title="Manhwa & Manhua Rankings API",
    description="Aggregated manga rankings from MangaDex, AniList, and Kitsu.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = deps.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route modules ──────────────────────────────────────────────
app.include_router(manga.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(feedback.router)
app.include_router(proxy.router)


# ── Run directly ───────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
