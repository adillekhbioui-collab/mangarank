"""
backend/deps.py

Shared state, Supabase helpers, cache utilities, and FastAPI dependencies
used by all route modules. Import from here – never from main.py – to
avoid circular imports.
"""

import os
import time
import math
from datetime import datetime, timedelta
from itertools import combinations
from collections import Counter
from typing import Optional
import secrets

import httpx
from slowapi import Limiter
from slowapi.util import get_remote_address
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Header

# ── Load environment ───────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip().replace("\n", "").replace("\r", "")
ADMIN_PASSWORD = (os.getenv("ADMIN_PASSWORD") or "").strip()


# ── Async HTTP client ──────────────────────────────────────────
# The client is created in main.py's lifespan() and injected via set_http_client().
# Route modules access it via deps.http_client.

http_client: httpx.AsyncClient | None = None


def set_http_client(client: httpx.AsyncClient) -> None:
    """Called from main.py lifespan to inject the shared client."""
    global http_client
    http_client = client


# ── Rate Limiter ───────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Supabase helpers ───────────────────────────────────────────

def sb_headers(count: bool = False) -> dict:
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if count:
        h["Prefer"] = "count=exact"
    return h


async def sb_get(path: str, params: dict | None = None, count: bool = False) -> httpx.Response:
    """Perform an async GET against the Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    return await http_client.get(url, headers=sb_headers(count), params=params)


async def sb_post(path: str, payload: object) -> httpx.Response:
    """Perform an async POST against the Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    return await http_client.post(url, headers=sb_headers(), json=payload)


def parse_total(response: httpx.Response) -> int | None:
    """Extract total count from Supabase content-range header."""
    cr = response.headers.get("content-range", "")
    if "/" in cr:
        try:
            return int(cr.split("/")[1])
        except (ValueError, IndexError):
            pass
    return None


# ── In-memory cache ────────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL = 600  # 10 minutes


def cache_get(key: str, ttl_override: int | None = None):
    entry = _cache.get(key)
    ttl = ttl_override if ttl_override is not None else CACHE_TTL
    if entry and (time.time() - entry[0]) < ttl:
        return entry[1]
    return None


def cache_set(key: str, value: object):
    _cache[key] = (time.time(), value)


# ── Admin auth dependency ──────────────────────────────────────

def require_admin(x_admin_password: Optional[str] = Header(default=None, alias="X-Admin-Password")):
    """FastAPI dependency: validates the X-Admin-Password header."""
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Admin endpoints are not configured.")
    if not x_admin_password or not secrets.compare_digest(x_admin_password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Shared query helpers ───────────────────────────────────────

async def count_query(path: str) -> int:
    r = await sb_get(path, count=True)
    if r.status_code not in (200, 206):
        raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")
    return parse_total(r) or 0


async def fetch_event_rows(
    event_type: str,
    days: int,
    select: str,
    extra_filters: dict[str, str] | None = None,
) -> list[dict]:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    page_size = 1000
    offset = 0
    out: list[dict] = []
    base_filters = {
        "select": select,
        "event_type": f"eq.{event_type}",
        "created_at": f"gte.{cutoff}",
    }

    if extra_filters:
        base_filters.update(extra_filters)

    while True:
        params = {
            **base_filters,
            "offset": str(offset),
            "limit": str(page_size),
        }
        r = await sb_get("events", params=params)
        if r.status_code not in (200, 206):
            raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

        rows = r.json()
        if not rows:
            break
        out.extend(rows)

        if len(rows) < page_size:
            break
        offset += page_size

    return out


# ── Genre relationship computation (cached 24h) ────────────────

_genre_relationships_cache: dict = {"data": None, "expires": None}


async def compute_genre_relationships() -> dict:
    genre_counts: Counter = Counter()
    genre_scores: dict[str, list[float]] = {}
    edge_counts: Counter = Counter()
    total_manga = 0

    offset = 0
    page_size = 1000

    while True:
        query = (
            f"manga_rankings?select=genres,aggregated_score"
            f"&aggregated_score=not.is.null&offset={offset}&limit={page_size}"
        )
        r = await sb_get(query)
        if r.status_code not in (200, 206):
            raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

        rows = r.json()
        if not rows:
            break

        for row in rows:
            genres = sorted({g for g in (row.get("genres") or []) if g})
            if not genres:
                continue

            score = row.get("aggregated_score")
            total_manga += 1

            for genre in genres:
                genre_counts[genre] += 1
                genre_scores.setdefault(genre, []).append(score)

            if len(genres) > 1:
                for a, b in combinations(genres, 2):
                    edge_counts[(a, b)] += 1

        if len(rows) < page_size:
            break
        offset += page_size

    max_co_occurrence = max(edge_counts.values()) if edge_counts else 1

    sorted_edges = sorted(
        (
            (a, b, count)
            for (a, b), count in edge_counts.items()
            if count >= 10
        ),
        key=lambda x: x[2],
        reverse=True,
    )[:300]

    node_genres = {a for a, _, _ in sorted_edges} | {b for _, b, _ in sorted_edges}

    nodes = [
        {
            "genre": genre,
            "manga_count": genre_counts[genre],
            "avg_score": round(sum(genre_scores[genre]) / len(genre_scores[genre]), 2),
        }
        for genre in sorted(node_genres, key=lambda g: genre_counts[g], reverse=True)
    ]

    edges = [
        {
            "genre_a": a,
            "genre_b": b,
            "co_occurrence": count,
            "strength": round(count / max_co_occurrence, 4),
        }
        for a, b, count in sorted_edges
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "total_manga": total_manga,
            "total_genres": len(genre_counts),
            "computed_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        },
    }


async def get_relationships_cached() -> dict:
    now = datetime.utcnow()
    expires = _genre_relationships_cache.get("expires")
    if _genre_relationships_cache["data"] is None or expires is None or now > expires:
        _genre_relationships_cache["data"] = await compute_genre_relationships()
        _genre_relationships_cache["expires"] = now + timedelta(hours=24)
    return _genre_relationships_cache["data"]
