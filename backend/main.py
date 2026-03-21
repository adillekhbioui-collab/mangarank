"""
Step 11 — Backend API (FastAPI).

Exposes five endpoints for querying manga rankings data stored in
Supabase. Supports filtering, sorting, pagination and CORS.

Run: uvicorn backend.main:app --reload --port 8000
"""

import os
import time
import math
import csv
from datetime import datetime, timedelta
from typing import Optional
from collections import Counter
from contextlib import asynccontextmanager
from itertools import combinations

import io
import hashlib
import httpx
import uvicorn
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

# ── Load environment ────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_allowed_origins() -> list[str]:
    """Return normalized CORS origins from env or safe defaults."""
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    if raw:
        origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
        return origins

    # Defaults cover local Vite dev plus common production hostname variants.
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://manhwa-rank.vercel.app",
    ]

# ── Async HTTP client (created at startup, closed on shutdown) ──
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=15)
    yield
    await http_client.aclose()


# ── FastAPI app ─────────────────────────────────────────────
app = FastAPI(
    title="Manhwa & Manhua Rankings API",
    description="Aggregated manga rankings from MangaDex, AniList, and Kitsu.",
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Supabase helpers ────────────────────────────────────────

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


def parse_total(response: httpx.Response) -> int | None:
    """Extract total count from Supabase content-range header."""
    cr = response.headers.get("content-range", "")
    if "/" in cr:
        try:
            return int(cr.split("/")[1])
        except (ValueError, IndexError):
            pass
    return None


# ── In-memory cache ─────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL = 600  # 10 minutes
_genre_relationships_cache = {"data": None, "expires": None}


def cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None


def cache_set(key: str, value: object):
    _cache[key] = (time.time(), value)


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


# ── Image Disk Cache ────────────────────────────────────────

IMAGE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache", "images")
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)


# ── Sort-by mapping ─────────────────────────────────────────

SORT_MAP = {
    "score": "aggregated_score",
    "views": "popularity_score",
    "chapters": "chapter_count",
    "completion": "completion_rate",
}

# ── Columns we actually need on the list endpoint ───────────

MANGA_COLS = "title,author,genres,alt_titles,chapter_count,aggregated_score,total_views,popularity_score,status,cover_image,summary,completion_rate,total_readers"

# ── Category → filter mapping for /top/{category} ──────────

GENRE_CATEGORIES = {
    "action", "romance", "fantasy", "drama",
    "thriller", "supernatural",
}
STATUS_CATEGORIES = {"completed", "ongoing"}
BLACKLIST_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "genres_blacklist.csv")


def load_blacklisted_genres_from_csv() -> list[str]:
    """Return sorted unique blacklisted genres from genres_blacklist.csv."""
    if not os.path.exists(BLACKLIST_CSV_PATH):
        return []

    out: set[str] = set()
    with open(BLACKLIST_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue

            genre = (row.get("Genre") or row.get("genre") or "").strip()
            flag = (row.get("Blacklisted") or row.get("blacklisted") or "").strip().lower()

            if genre and flag in {"yes", "true", "1", "y"}:
                out.add(genre)

    return sorted(out)


# ────────────────────────────────────────────────────────────
#  GET /similar-manga/{title} — recommendations
# ────────────────────────────────────────────────────────────

@app.get("/similar-manga/{title}")
async def get_similar_manga_new(title: str, response: Response):
    """Return up to 6 similar manga based on shared genres and score proximity."""
    response.headers["Cache-Control"] = "public, max-age=300"

    cache_key = f"similar:{title}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/get_similar_manga"
    payload = {"target_title": title, "result_limit": 6}
    r = await http_client.post(
        rpc_url,
        headers=sb_headers(),
        json=payload,
    )

    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Failed to fetch similar manga.")

    result = {"results": r.json()}
    cache_set(cache_key, result)
    return result


# ────────────────────────────────────────────────────────────
#  GET /manga — paginated, filterable, sortable list
# ────────────────────────────────────────────────────────────

@app.get("/manga")
async def list_manga(
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
    # Instruct browser to cache these search results for 5 minutes
    response.headers["Cache-Control"] = "public, max-age=300"

    sort_col = SORT_MAP.get(sort_by, "aggregated_score")
    offset = (page - 1) * limit

    # Build Supabase query string — select only needed columns
    query = f"manga_rankings?select={MANGA_COLS}&order={sort_col}.desc.nullslast&offset={offset}&limit={limit}"

    if has_completion_data:
        query += "&completion_rate=not.is.null"

    # Legacy single genre (backwards compatible)
    if genre:
        query += f"&genres=cs.{{{genre}}}"

    # Multi-genre include: manga must contain ALL listed genres (cs = contains)
    if genre_include:
        csv = ",".join(genre_include)
        query += f"&genres=cs.{{{csv}}}"

    # Multi-genre exclude: manga must NOT overlap with ANY listed genre
    if genre_exclude:
        csv = ",".join(genre_exclude)
        query += f"&genres=not.ov.{{{csv}}}"

    if author:
        query += f"&author=ilike.*{author}*"
    if min_chapters is not None:
        query += f"&chapter_count=gte.{min_chapters}"
    if status:
        query += f"&status=eq.{status.lower()}"

    r = await sb_get(query, count=True)
    if r.status_code not in (200, 206):
        raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

    total_count = parse_total(r)
    total_pages = math.ceil(total_count / limit) if total_count is not None else None

    return {
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages,
        "results": r.json(),
    }


@app.get("/manga/{title}/similar")
async def get_similar_manga_endpoint(title: str, response: Response):
    """Return up to 6 similar manga based on shared genres and score proximity."""
    response.headers["Cache-Control"] = "public, max-age=300"

    cache_key = f"similar:{title}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/get_similar_manga"
    payload = {"target_title": title, "result_limit": 6}
    r = await http_client.post(
        rpc_url,
        headers=sb_headers(),
        json=payload,
    )

    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Failed to fetch similar manga.")

    result = {"results": r.json()}
    cache_set(cache_key, result)
    return result


# ────────────────────────────────────────────────────────────
#  GET /manga/{title} — single record by exact title
# ────────────────────────────────────────────────────────────

@app.get("/manga/{title}")
async def get_manga(title: str, response: Response):
    """Return a single manga record by exact title match. Returns 404 if not found."""
    response.headers["Cache-Control"] = "public, max-age=600"

    query = f"manga_rankings?select=*&title=eq.{title}&limit=1"
    r = await sb_get(query)

    if r.status_code not in (200, 206):
        raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

    data = r.json()
    if not data:
        raise HTTPException(status_code=404, detail=f"Manga '{title}' not found.")

    return data[0]


# ────────────────────────────────────────────────────────────
#  GET /genres — all unique genres (cached 10 min)
# ────────────────────────────────────────────────────────────

@app.get("/genres")
async def list_genres(response: Response):
    """Return a sorted list of all unique genre strings across all manga_rankings records."""
    response.headers["Cache-Control"] = "public, max-age=600"

    cached = cache_get("genres")
    if cached is not None:
        return cached

    all_genres: set[str] = set()
    offset = 0
    page_size = 1000

    while True:
        query = f"manga_rankings?select=genres&offset={offset}&limit={page_size}"
        r = await sb_get(query)
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
    cache_set("genres", result)
    return result


@app.get("/genres/blacklist")
async def list_blacklisted_genres(response: Response):
    """Return the current sorted blacklist genres from CSV (cached 10 min)."""
    response.headers["Cache-Control"] = "public, max-age=600"

    cached = cache_get("genres_blacklist")
    if cached is not None:
        return cached

    result = {"blacklist": load_blacklisted_genres_from_csv()}
    cache_set("genres_blacklist", result)
    return result


@app.get("/genres/relationships")
async def genres_relationships(response: Response):
    response.headers["Cache-Control"] = "public, max-age=86400"
    return await get_relationships_cached()


# ────────────────────────────────────────────────────────────
#  GET /top/{category} — top 20 by category
# ────────────────────────────────────────────────────────────

@app.get("/top/{category}")
async def top_by_category(category: str, response: Response):
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
            detail=f"Unknown category '{category}'. Valid: action, romance, fantasy, drama, "
                   "thriller, supernatural, completed, ongoing, long, short, completion-masterpieces, completion-traps, guilty-pleasures.",
        )

    r = await sb_get(query)
    if r.status_code not in (200, 206):
        raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

    # Optional label overrides for frontend display
    cat_label = cat
    if cat == "completion-masterpieces":
        cat_label = "Masterpieces"
    elif cat == "completion-traps":
        cat_label = "Hard to Finish"
    elif cat == "guilty-pleasures":
        cat_label = "Guilty Pleasures"

    return {"category": cat_label, "results": r.json()}


# ────────────────────────────────────────────────────────────
#  GET /stats — summary statistics (cached 10 min)
# ────────────────────────────────────────────────────────────

@app.get("/stats")
async def stats(response: Response):
    """
    Return summary stats: total manga, total sources, top 3 genres, and last updated time.
    """
    response.headers["Cache-Control"] = "public, max-age=600"

    cached = cache_get("stats")
    if cached is not None:
        return cached

    # Total manga
    total_manga = 0
    r_count = await http_client.get(
        f"{SUPABASE_URL}/rest/v1/manga_rankings?select=id",
        headers={**sb_headers(), "Prefer": "count=exact"},
        params={"limit": "0"},
    )
    cr = r_count.headers.get("content-range", "")
    if "/" in cr:
        try:
            total_manga = int(cr.split("/")[1])
        except (ValueError, IndexError):
            total_manga = 0

    # Total distinct sources in manga_raw
    r_sources = await sb_get("manga_raw?select=source_site", params={"limit": "1000"})
    if r_sources.status_code in (200, 206):
        sites = set(row.get("source_site") for row in r_sources.json())
        total_sources = len(sites)
    else:
        total_sources = 0

    # Top 3 genres
    genre_counter: Counter = Counter()
    offset = 0
    while True:
        rg = await sb_get(f"manga_rankings?select=genres&offset={offset}&limit=1000")
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
    r_updated = await sb_get("manga_rankings?select=updated_at&order=updated_at.desc&limit=1")
    last_updated = None
    if r_updated.status_code in (200, 206):
        rows = r_updated.json()
        if rows:
            last_updated = rows[0].get("updated_at")

    # Completion Rate Stats
    r_completion = await sb_get("manga_rankings?select=completion_rate&completion_rate=not.is.null")
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
    cache_set("stats", result)
    return result


# ────────────────────────────────────────────────────────────
#  GET /proxy/image — resize and cache cover images
# ────────────────────────────────────────────────────────────

def process_image(content: bytes, cache_path: str):
    # Resize and convert to WebP
    img = Image.open(io.BytesIO(content))
    if img.mode != "RGB":
        # Convert RGBA to RGB using a white background if needed
        if img.mode == 'RGBA':
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert("RGB")
    
    # Resize to 300px width, maintaining aspect ratio
    target_width = 300
    if img.size[0] > target_width:
        wpercent = (target_width / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((target_width, hsize), Image.Resampling.LANCZOS)
    
    # Save to disk cache
    img.save(cache_path, "WEBP", quality=80)


@app.get("/proxy/image")
async def proxy_image(url: str, response: Response):
    """Fetch, resize, cache, and serve optimized (300px WebP) cover images."""
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")
    
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_path = os.path.join(IMAGE_CACHE_DIR, f"{url_hash}.webp")
    
    # Serve from disk cache if exists
    if os.path.exists(cache_path):
        response.headers["Cache-Control"] = "public, max-age=86400"
        return FileResponse(cache_path, media_type="image/webp")
    
    # Fetch from source
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = await http_client.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"Proxy fetch failed for {url}: {e}")
        raise HTTPException(status_code=404, detail="Image not found")
        
    try:
        # Resize and convert to WebP using threadpool
        await run_in_threadpool(process_image, r.content, cache_path)
        
        response.headers["Cache-Control"] = "public, max-age=86400"
        return FileResponse(cache_path, media_type="image/webp")
    except Exception as e:
        print(f"Error processing image {url}: {e}")
        # Fallback to original image
        return Response(content=r.content, media_type=r.headers.get("content-type", "image/jpeg"))


# ────────────────────────────────────────────────────────────
#  Run directly
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
