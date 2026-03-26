"""
backend/routes/admin.py

Protected admin endpoints — all require the X-Admin-Password header.
Auth is enforced at router level (single Depends call) rather than per-endpoint.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request

from backend import deps

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(deps.require_admin)],
)


@router.get("/stats")
@deps.limiter.limit("30/minute")
async def admin_stats(request: Request, response: Response):
    response.headers["Cache-Control"] = "private, max-age=60"

    cached = deps.cache_get("admin:stats", ttl_override=120)
    if cached is not None:
        return cached

    total_count = await deps.count_query("manga_rankings?select=id&limit=0")
    unscored_count = await deps.count_query("manga_rankings?select=id&aggregated_score=is.null&limit=0")
    raw_count = await deps.count_query("manga_raw?select=id&limit=0")

    r_updated = await deps.sb_get("manga_rankings?select=updated_at&order=updated_at.desc&limit=1")
    if r_updated.status_code not in (200, 206):
        raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

    last_updated = None
    rows = r_updated.json()
    if rows:
        last_updated = rows[0].get("updated_at")

    scored_count = max(0, total_count - unscored_count)
    score_rate = round((scored_count / total_count) * 100, 1) if total_count else 0.0

    result = {
        "total_manga": total_count,
        "scored_manga": scored_count,
        "unscored_manga": unscored_count,
        "score_rate_pct": score_rate,
        "total_raw_records": raw_count,
        "last_updated": last_updated,
    }
    deps.cache_set("admin:stats", result)
    return result


@router.get("/source-health")
@deps.limiter.limit("30/minute")
async def admin_source_health(request: Request, response: Response):
    response.headers["Cache-Control"] = "private, max-age=120"

    cached = deps.cache_get("admin:source-health", ttl_override=180)
    if cached is not None:
        return cached

    sources = ["anilist", "mal", "mangadex", "kitsu"]
    output = []

    for source in sources:
        total = await deps.count_query(f"manga_raw?select=id&source_site=eq.{source}&limit=0")
        null_rating = await deps.count_query(
            f"manga_raw?select=id&source_site=eq.{source}&rating=is.null&limit=0"
        )
        null_views = await deps.count_query(
            f"manga_raw?select=id&source_site=eq.{source}&view_count=is.null&limit=0"
        )
        output.append(
            {
                "source": source,
                "total_records": total,
                "null_rating_count": null_rating,
                "null_rating_pct": round((null_rating / total) * 100, 1) if total else 0.0,
                "null_views_count": null_views,
                "null_views_pct": round((null_views / total) * 100, 1) if total else 0.0,
            }
        )

    deps.cache_set("admin:source-health", output)
    return output


@router.get("/score-distribution")
@deps.limiter.limit("30/minute")
async def admin_score_distribution(request: Request, response: Response):
    response.headers["Cache-Control"] = "private, max-age=300"

    cached = deps.cache_get("admin:score-distribution", ttl_override=600)
    if cached is not None:
        return cached

    buckets = []
    for start in range(0, 100, 10):
        end = 101 if start == 90 else start + 10
        count = await deps.count_query(
            f"manga_rankings?select=id&aggregated_score=gte.{start}&aggregated_score=lt.{end}&limit=0"
        )
        buckets.append({"range": f"{start}-{start + 10}", "count": count})

    deps.cache_set("admin:score-distribution", buckets)
    return buckets


@router.get("/coverage")
@deps.limiter.limit("30/minute")
async def admin_coverage(request: Request, response: Response):
    response.headers["Cache-Control"] = "private, max-age=300"

    cached = deps.cache_get("admin:coverage", ttl_override=900)
    if cached is not None:
        return cached

    title_sources: dict[str, set[str]] = defaultdict(set)
    offset = 0
    page_size = 5000

    while True:
        query = f"manga_raw?select=title,source_site&offset={offset}&limit={page_size}"
        r = await deps.sb_get(query)
        if r.status_code not in (200, 206):
            raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

        rows = r.json()
        if not rows:
            break

        for row in rows:
            title = (row.get("title") or "").strip()
            source = (row.get("source_site") or "").strip()
            if title and source:
                title_sources[title].add(source)

        if len(rows) < page_size:
            break
        offset += page_size

    distribution: dict[int, int] = defaultdict(int)
    for sources in title_sources.values():
        distribution[len(sources)] += 1

    result = [
        {"sources": source_count, "manga_count": count}
        for source_count, count in sorted(distribution.items())
    ]

    deps.cache_set("admin:coverage", result)
    return result


@router.get("/analytics/searches")
@deps.limiter.limit("30/minute")
async def admin_analytics_searches(
    request: Request,
    response: Response,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
):
    response.headers["Cache-Control"] = "private, max-age=180"
    cache_key = f"admin:analytics:searches:{days}:{limit}"
    cached = deps.cache_get(cache_key, ttl_override=300)
    if cached is not None:
        return cached

    rows = await deps.fetch_event_rows("search", days, "metadata")
    counts: Counter = Counter()
    for row in rows:
        query = ((row.get("metadata") or {}).get("query") or "").strip().lower()
        if query:
            counts[query] += 1

    result = [{"query": q, "count": c} for q, c in counts.most_common(limit)]
    deps.cache_set(cache_key, result)
    return result


@router.get("/analytics/manga-views")
@deps.limiter.limit("30/minute")
async def admin_analytics_manga_views(
    request: Request,
    response: Response,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
):
    response.headers["Cache-Control"] = "private, max-age=180"
    cache_key = f"admin:analytics:manga-views:{days}:{limit}"
    cached = deps.cache_get(cache_key, ttl_override=300)
    if cached is not None:
        return cached

    rows = await deps.fetch_event_rows(
        "manga_view",
        days,
        "manga_title",
        extra_filters={"manga_title": "not.is.null"},
    )
    counts: Counter = Counter()
    for row in rows:
        title = (row.get("manga_title") or "").strip()
        if title:
            counts[title] += 1

    result = [{"title": t, "views": c} for t, c in counts.most_common(limit)]
    deps.cache_set(cache_key, result)
    return result


@router.get("/analytics/filters")
@deps.limiter.limit("30/minute")
async def admin_analytics_filters(
    request: Request,
    response: Response,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(15, ge=1, le=100),
):
    response.headers["Cache-Control"] = "private, max-age=180"
    cache_key = f"admin:analytics:filters:{days}:{limit}"
    cached = deps.cache_get(cache_key, ttl_override=300)
    if cached is not None:
        return cached

    rows = await deps.fetch_event_rows(
        "filter_applied",
        days,
        "filter_state",
        extra_filters={"filter_state": "not.is.null"},
    )

    combos: Counter = Counter()
    for row in rows:
        fs = row.get("filter_state") or {}
        if not isinstance(fs, dict):
            continue

        parts = []
        include = fs.get("genre_include") or []
        if include:
            parts.append(f"include:{','.join(include[:2])}")

        status = fs.get("status")
        if status and status != "all":
            parts.append(f"status:{status}")

        sort_by = fs.get("sort_by")
        if sort_by and sort_by != "score":
            parts.append(f"sort:{sort_by}")

        if parts:
            combos[" + ".join(parts)] += 1

    result = [{"combination": k, "count": v} for k, v in combos.most_common(limit)]
    deps.cache_set(cache_key, result)
    return result


@router.get("/analytics/watchlist")
@deps.limiter.limit("30/minute")
async def admin_analytics_watchlist(
    request: Request,
    response: Response,
    days: int = Query(30, ge=1, le=365),
):
    response.headers["Cache-Control"] = "private, max-age=180"
    cache_key = f"admin:analytics:watchlist:{days}"
    cached = deps.cache_get(cache_key, ttl_override=300)
    if cached is not None:
        return cached

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    page_size = 1000
    offset = 0
    rows: list[dict] = []

    while True:
        params = {
            "select": "created_at,event_type,manga_title",
            "event_type": "in.(watchlist_add,watchlist_remove)",
            "created_at": f"gte.{cutoff}",
            "order": "created_at.asc",
            "offset": str(offset),
            "limit": str(page_size),
        }
        r = await deps.sb_get("events", params=params)
        if r.status_code not in (200, 206):
            raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")

        batch = r.json()
        if not batch:
            break
        rows.extend(batch)

        if len(batch) < page_size:
            break
        offset += page_size

    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"adds": 0, "removes": 0})
    top_added_counts: Counter = Counter()

    for row in rows:
        day = (row.get("created_at") or "")[:10]
        event_type = row.get("event_type")
        title = (row.get("manga_title") or "").strip()
        if not day:
            continue

        if event_type == "watchlist_add":
            daily[day]["adds"] += 1
            if title:
                top_added_counts[title] += 1
        elif event_type == "watchlist_remove":
            daily[day]["removes"] += 1

    result = {
        "daily": [{"date": d, **v} for d, v in sorted(daily.items())],
        "top_added": [{"title": t, "count": c} for t, c in top_added_counts.most_common(10)],
    }
    deps.cache_set(cache_key, result)
    return result


@router.get("/analytics/users")
@deps.limiter.limit("30/minute")
async def admin_analytics_users(request: Request, response: Response):
    response.headers["Cache-Control"] = "private, max-age=300"
    
    cached = deps.cache_get("admin:analytics:users", ttl_override=600)
    if cached is not None:
        return cached

    now = datetime.utcnow()
    cutoff_30d = (now - timedelta(days=30)).isoformat()
    
    page_size = 5000
    offset = 0
    rows = []

    while True:
        params = {
            "select": "created_at,user_id,session_id",
            "created_at": f"gte.{cutoff_30d}",
            "offset": str(offset),
            "limit": str(page_size),
        }
        r = await deps.sb_get("events", params=params)
        if r.status_code not in (200, 206):
            raise HTTPException(status_code=502, detail="Failed to fetch from Supabase.")
            
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        
        if len(batch) < page_size:
            break
        offset += page_size

    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    dau_users, dau_sessions = set(), set()
    wau_users, wau_sessions = set(), set()
    mau_users, mau_sessions = set(), set()
    
    for row in rows:
        dt_str = row.get("created_at", "")
        if not dt_str:
            continue
        
        # handle timezone safely
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            try:
                dt = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue
            
        uid = row.get("user_id")
        sid = row.get("session_id")
        
        if uid:
            mau_users.add(uid)
            if dt >= week_ago:
                wau_users.add(uid)
            if dt >= day_ago:
                dau_users.add(uid)
        elif sid:
            mau_sessions.add(sid)
            if dt >= week_ago:
                wau_sessions.add(sid)
            if dt >= day_ago:
                dau_sessions.add(sid)

    result = {
        "dau": {"registered": len(dau_users), "anonymous": len(dau_sessions), "total": len(dau_users) + len(dau_sessions)},
        "wau": {"registered": len(wau_users), "anonymous": len(wau_sessions), "total": len(wau_users) + len(wau_sessions)},
        "mau": {"registered": len(mau_users), "anonymous": len(mau_sessions), "total": len(mau_users) + len(mau_sessions)}
    }
    
    deps.cache_set("admin:analytics:users", result)
    return result
