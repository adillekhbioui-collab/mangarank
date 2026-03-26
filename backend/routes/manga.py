"""
backend/routes/manga.py

Public discovery endpoints: manga listing, detail, similar, genres, top, stats.
"""

import math
from collections import Counter
from typing import Optional

import re
from fastapi import APIRouter, HTTPException, Query, Response, Request

from backend import deps
from backend.constants import (
    GENRE_CATEGORIES,
    MANGA_COLS,
    SORT_MAP,
    STATUS_CATEGORIES,
    load_blacklisted_genres_from_csv,
)

router = APIRouter(tags=["manga"])


# ── GET /manga — paginated, filterable, sortable list ────────

def sanitize_param(val: str) -> str:
    """Strip characters that could manipulate PostgREST syntax."""
    return re.sub(r'[&={}()*/]', '', val)

@router.get("/manga")
@deps.limiter.limit("100/minute")
async def list_manga(
    request: Request,
    response: Response,
    genre: Optional[str] = Query(None, description="Filter by single genre tag (legacy)."),
    genre_include: list[str] = Query([], description="Genres the manga MUST have (AND logic)."),
    genre_exclude: list[str] = Query([], description="Genres the manga must NOT have (ANY match excludes)."),
    author: Optional[str] = Query(None, description="Filter by author name (partial match)."),
    min_chapters: Optional[int] = Query(None, description="Minimum chapter count."),
    status: Optional[str] = Query(None, description="Filter by 'ongoing' or 'completed'."),
    has_completion_data: bool = Query(False, description="Only show manga with completion data."),
    sort_by: str = Query("score", description="Sort field: score, views, chapters, or completion."),
    limit: int = Query(20, ge=1, le=100, description="Results per page (max 100)."),
    page: int = Query(1, ge=1, description="Page number."),
):
    """Return a paginated list of manga from manga_rankings, with optional filters and sorting."""
    response.headers["Cache-Control"] = "public, max-age=300"

    sort_col = SORT_MAP.get(sort_by, "aggregated_score")
    offset = (page - 1) * limit

    query = f"manga_rankings?select={MANGA_COLS}&order={sort_col}.desc.nullslast&offset={offset}&limit={limit}"

    if has_completion_data:
        query += "&completion_rate=not.is.null"

    # Legacy single genre (backwards compatible)
    if genre:
        query += f"&genres=cs.{{{sanitize_param(genre)}}}"

    # Multi-genre include: manga must contain ALL listed genres
    if genre_include:
        clean_includes = [sanitize_param(g) for g in genre_include]
        csv = ",".join(clean_includes)
        query += f"&genres=cs.{{{csv}}}"

    # Multi-genre exclude: manga must NOT overlap with ANY listed genre
    if genre_exclude:
        clean_excludes = [sanitize_param(g) for g in genre_exclude]
        csv = ",".join(clean_excludes)
        query += f"&genres=not.ov.{{{csv}}}"

    if author:
        query += f"&author=ilike.*{sanitize_param(author)}*"
    if min_chapters is not None:
        query += f"&chapter_count=gte.{min_chapters}"
    if status:
        query += f"&status=eq.{status.lower()}"

    r = await deps.sb_get(query, count=True)
    if r.status_code not in (200, 206):
        raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

    total_count = deps.parse_total(r)
    total_pages = math.ceil(total_count / limit) if total_count is not None else None

    return {
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages,
        "results": r.json(),
    }


# ── GET /manga/{title}/similar — must be declared before /{title} ──

@router.get("/manga/{title}/similar")
@deps.limiter.limit("100/minute")
async def get_similar_manga_endpoint(request: Request, title: str, response: Response):
    """Return up to 6 similar manga based on shared genres and score proximity."""
    response.headers["Cache-Control"] = "public, max-age=300"

    cache_key = f"similar:{title}"
    cached = deps.cache_get(cache_key)
    if cached is not None:
        return cached

    from backend import deps as _deps  # local import to avoid re-importing module
    rpc_url = f"{_deps.SUPABASE_URL}/rest/v1/rpc/get_similar_manga"
    payload = {"target_title": title, "result_limit": 6}
    r = await deps.http_client.post(rpc_url, headers=deps.sb_headers(), json=payload)

    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Failed to fetch similar manga.")

    result = {"results": r.json()}
    deps.cache_set(cache_key, result)
    return result


# ── GET /manga/{title} — single record ───────────────────────

@router.get("/manga/{title}")
@deps.limiter.limit("100/minute")
async def get_manga(request: Request, title: str, response: Response):
    """Return a single manga record by exact title match. Returns 404 if not found."""
    response.headers["Cache-Control"] = "public, max-age=600"

    query = f"manga_rankings?select=*&title=eq.{title}&limit=1"
    r = await deps.sb_get(query)

    if r.status_code not in (200, 206):
        raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

    data = r.json()
    if not data:
        raise HTTPException(status_code=404, detail=f"Manga '{title}' not found.")

    return data[0]


# ── GET /similar-manga/{title} — legacy alias ─────────────────

@router.get("/similar-manga/{title}")
@deps.limiter.limit("100/minute")
async def get_similar_manga_new(request: Request, title: str, response: Response):
    """Return up to 6 similar manga based on shared genres and score proximity."""
    response.headers["Cache-Control"] = "public, max-age=300"

    cache_key = f"similar:{title}"
    cached = deps.cache_get(cache_key)
    if cached is not None:
        return cached

    rpc_url = f"{deps.SUPABASE_URL}/rest/v1/rpc/get_similar_manga"
    payload = {"target_title": title, "result_limit": 6}
    r = await deps.http_client.post(rpc_url, headers=deps.sb_headers(), json=payload)

    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Failed to fetch similar manga.")

    result = {"results": r.json()}
    deps.cache_set(cache_key, result)
    return result


# ── GET /genres ───────────────────────────────────────────────

@router.get("/genres")
@deps.limiter.limit("60/minute")
async def list_genres(request: Request, response: Response):
    """Return a sorted list of all unique genre strings across all manga_rankings records."""
    response.headers["Cache-Control"] = "public, max-age=600"

    cached = deps.cache_get("genres")
    if cached is not None:
        return cached

    all_genres: set[str] = set()
    offset = 0
    page_size = 1000

    while True:
        query = f"manga_rankings?select=genres&offset={offset}&limit={page_size}"
        r = await deps.sb_get(query)
        if r.status_code not in (200, 206):
            break
        rows = r.json()
        if not rows:
            break
        for row in rows:
            for g in (row.get("genres") or []):
                all_genres.add(g)
        if len(rows) < page_size:
            break
        offset += page_size

    result = {"genres": sorted(all_genres)}
    deps.cache_set("genres", result)
    return result


@router.get("/genres/blacklist")
@deps.limiter.limit("60/minute")
async def list_blacklisted_genres(request: Request, response: Response):
    """Return the current sorted blacklist genres from CSV (cached 10 min)."""
    response.headers["Cache-Control"] = "public, max-age=600"

    cached = deps.cache_get("genres_blacklist")
    if cached is not None:
        return cached

    result = {"blacklist": load_blacklisted_genres_from_csv()}
    deps.cache_set("genres_blacklist", result)
    return result


@router.get("/genres/relationships")
@deps.limiter.limit("60/minute")
async def genres_relationships(request: Request, response: Response):
    response.headers["Cache-Control"] = "public, max-age=86400"
    return await deps.get_relationships_cached()


# ── GET /top/{category} ───────────────────────────────────────

@router.get("/top/{category}")
@deps.limiter.limit("100/minute")
async def top_by_category(request: Request, category: str, response: Response):
    """
    Return the top 20 manga for a category sorted by aggregated_score desc.
    Categories: action, romance, fantasy, drama, thriller, supernatural,
                completed, ongoing, long (≥100 chapters), short (<20 chapters),
                completion-masterpieces, completion-traps, guilty-pleasures.
    """
    response.headers["Cache-Control"] = "public, max-age=300"

    cat = category.lower()
    query = f"manga_rankings?select={MANGA_COLS}&limit=20"

    if cat in GENRE_CATEGORIES:
        genre_name = cat.title()
        query += f"&genres=cs.{{{genre_name}}}&order=aggregated_score.desc.nullslast"
    elif cat in STATUS_CATEGORIES:
        query += f"&status=eq.{cat}&order=aggregated_score.desc.nullslast"
    elif cat == "long":
        query += "&chapter_count=gte.100&order=aggregated_score.desc.nullslast"
    elif cat == "short":
        query += "&chapter_count=lt.20&order=aggregated_score.desc.nullslast"
    elif cat == "completion-masterpieces":
        query += "&aggregated_score=gte.75&completion_rate=gte.60&total_readers=gte.1000&order=completion_rate.desc.nullslast"
    elif cat == "completion-traps":
        query += "&aggregated_score=gte.75&completion_rate=lt.35&total_readers=gte.2000&order=aggregated_score.desc.nullslast"
    elif cat == "guilty-pleasures":
        query += "&aggregated_score=lt.70&completion_rate=gte.65&total_readers=gte.1000&order=completion_rate.desc.nullslast"
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown category '{category}'. Valid: action, romance, fantasy, drama, "
                "thriller, supernatural, completed, ongoing, long, short, "
                "completion-masterpieces, completion-traps, guilty-pleasures."
            ),
        )

    r = await deps.sb_get(query)
    if r.status_code not in (200, 206):
        raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

    cat_label = cat
    if cat == "completion-masterpieces":
        cat_label = "Masterpieces"
    elif cat == "completion-traps":
        cat_label = "Hard to Finish"
    elif cat == "guilty-pleasures":
        cat_label = "Guilty Pleasures"

    return {"category": cat_label, "results": r.json()}


# ── GET /stats ────────────────────────────────────────────────

@router.get("/stats")
@deps.limiter.limit("60/minute")
async def stats(request: Request, response: Response):
    """Return summary stats: total manga, total sources, top 3 genres, and last updated time."""
    response.headers["Cache-Control"] = "public, max-age=600"

    cached = deps.cache_get("stats")
    if cached is not None:
        return cached

    # Total manga
    total_manga = 0
    r_count = await deps.http_client.get(
        f"{deps.SUPABASE_URL}/rest/v1/manga_rankings?select=id",
        headers={**deps.sb_headers(), "Prefer": "count=exact"},
        params={"limit": "0"},
    )
    cr = r_count.headers.get("content-range", "")
    if "/" in cr:
        try:
            total_manga = int(cr.split("/")[1])
        except (ValueError, IndexError):
            total_manga = 0

    # Total distinct sources
    r_sources = await deps.sb_get("manga_raw?select=source_site", params={"limit": "1000"})
    if r_sources.status_code in (200, 206):
        sites = {row.get("source_site") for row in r_sources.json()}
        total_sources = len(sites)
    else:
        total_sources = 0

    # Top 3 genres
    genre_counter: Counter = Counter()
    offset = 0
    while True:
        rg = await deps.sb_get(f"manga_rankings?select=genres&offset={offset}&limit=1000")
        if rg.status_code not in (200, 206):
            break
        rows = rg.json()
        if not rows:
            break
        for row in rows:
            for g in (row.get("genres") or []):
                genre_counter[g] += 1
        if len(rows) < 1000:
            break
        offset += 1000
    top_genres = [g for g, _ in genre_counter.most_common(3)]

    # Last updated
    r_updated = await deps.sb_get("manga_rankings?select=updated_at&order=updated_at.desc&limit=1")
    last_updated = None
    if r_updated.status_code in (200, 206):
        rows = r_updated.json()
        if rows:
            last_updated = rows[0].get("updated_at")

    # Completion rate stats
    r_completion = await deps.sb_get("manga_rankings?select=completion_rate&completion_rate=not.is.null")
    avg_completion = None
    completion_count = 0
    if r_completion.status_code in (200, 206):
        rows = r_completion.json()
        completion_count = len(rows)
        if completion_count > 0:
            avg_completion = sum(r.get("completion_rate", 0) for r in rows) / completion_count
            avg_completion = round(avg_completion, 1)

    result = {
        "total_manga": total_manga,
        "total_sources": total_sources,
        "top_genres": top_genres,
        "last_updated": last_updated,
        "average_completion_rate": avg_completion,
        "manga_with_completion_data": completion_count,
    }
    deps.cache_set("stats", result)
    return result
