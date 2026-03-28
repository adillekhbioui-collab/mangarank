"""
Step 3 — Fetch manhwa & manhua data from the MangaDex API.

Paginates through all Korean (ko) and Chinese (zh) manga,
resolves author names, chapter counts, and cover images via
additional API calls, then upserts every record into the
Supabase manga_raw table with source_site = 'mangadex'.
"""

import os
import sys
import json
import time
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ── Load environment ────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

MANGADEX_BASE = "https://api.mangadex.org"
COVERS_BASE = "https://uploads.mangadex.org/covers"
DELAY = 0.5  # seconds between API calls

# ── Caches ──────────────────────────────────────────────────
author_cache: dict[str, str] = {}   # author_id -> name
cover_cache: dict[str, str] = {}    # cover_id  -> filename

# ── HTTP client ─────────────────────────────────────────────
client = httpx.Client(timeout=30, follow_redirects=True)


def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


# ────────────────────────────────────────────────────────────
#  Helper functions
# ────────────────────────────────────────────────────────────

def safe_get(url: str, params: dict | None = None) -> dict | None:
    """GET with retry (up to 3 attempts) and rate-limit delay."""
    for attempt in range(3):
        try:
            time.sleep(DELAY)
            r = client.get(url, params=params)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", 5))
                print(f"    Rate-limited, waiting {wait}s …")
                time.sleep(wait)
                continue
            print(f"    ⚠ {url} returned {r.status_code}")
            return None
        except httpx.HTTPError as e:
            print(f"    ⚠ HTTP error on attempt {attempt+1}: {e}")
            time.sleep(2)
    return None


def extract_title(attributes: dict) -> str:
    """Get the English title, falling back to first available."""
    # Primary title object
    title_obj = attributes.get("title", {})
    if "en" in title_obj:
        return title_obj["en"]
    # Alt titles
    for alt in attributes.get("altTitles", []):
        if "en" in alt:
            return alt["en"]
    # Fallback: first value found
    if title_obj:
        return next(iter(title_obj.values()))
    for alt in attributes.get("altTitles", []):
        if alt:
            return next(iter(alt.values()))
    return "Unknown Title"


def extract_summary(attributes: dict) -> str | None:
    """Pull English description/summary."""
    description_obj = attributes.get("description", {})
    if "en" in description_obj:
        return description_obj["en"]
    # Fallback to the first available if no English summary
    if description_obj:
        return next(iter(description_obj.values()))
    return None


def extract_alt_titles(attributes: dict) -> list[str]:
    """Flatten all alternative titles into a unique list."""
    out: list[str] = []
    seen: set[str] = set()
    for alt in attributes.get("altTitles", []):
        if not isinstance(alt, dict):
            continue
        for value in alt.values():
            if not isinstance(value, str):
                continue
            clean = value.strip()
            if not clean:
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(clean)
    return out


def extract_genres(attributes: dict) -> list[str]:
    """Pull English genre/tag names from the tags array."""
    genres = []
    for tag in attributes.get("tags", []):
        name = tag.get("attributes", {}).get("name", {}).get("en")
        if name:
            genres.append(name)
    return genres


def fetch_author_name(author_id: str) -> str | None:
    """Resolve an author id to a name, with caching."""
    if author_id in author_cache:
        return author_cache[author_id]

    data = safe_get(f"{MANGADEX_BASE}/author/{author_id}")
    if data and "data" in data:
        name = data["data"].get("attributes", {}).get("name")
        author_cache[author_id] = name
        return name
    return None


def fetch_chapter_count(manga_id: str) -> int:
    """Count total chapters via the aggregate endpoint."""
    data = safe_get(f"{MANGADEX_BASE}/manga/{manga_id}/aggregate",
                    params={"translatedLanguage[]": "en"})
    if not data or "volumes" not in data:
        return 0

    volumes = data["volumes"]
    if isinstance(volumes, list):
        return 0

    count = 0
    for vol in volumes.values():
        if isinstance(vol, dict) and "chapters" in vol:
            count += len(vol["chapters"])
    return count


def fetch_cover_url(manga_id: str, cover_id: str) -> str | None:
    """Resolve a cover_art relationship to a full image URL."""
    if cover_id in cover_cache:
        filename = cover_cache[cover_id]
        return f"{COVERS_BASE}/{manga_id}/{filename}"

    data = safe_get(f"{MANGADEX_BASE}/cover/{cover_id}")
    if data and "data" in data:
        filename = data["data"].get("attributes", {}).get("fileName")
        if filename:
            cover_cache[cover_id] = filename
            return f"{COVERS_BASE}/{manga_id}/{filename}"
    return None


def fetch_statistics(manga_id: str) -> tuple:
    """
    Fetch rating data from the MangaDex statistics endpoint.
    Returns (rating, rating_count, follows) or (None, None, None) if unavailable.
    """
    data = safe_get(f"{MANGADEX_BASE}/statistics/manga/{manga_id}")
    if not data or "statistics" not in data:
        return None, None, None

    stats = data["statistics"].get(manga_id, {})
    rating_obj = stats.get("rating", {})

    raw_score = rating_obj.get("bayesian") or rating_obj.get("average")
    if raw_score is None:
        return None, None, None

    normalized_score = round(float(raw_score) * 10, 2)
    distribution = rating_obj.get("distribution", {})
    total_votes = sum(distribution.values()) if distribution else None
    follows = stats.get("follows", None)

    return normalized_score, total_votes, follows


# ────────────────────────────────────────────────────────────
#  Main fetch loop
# ────────────────────────────────────────────────────────────

def fetch_all_manga(max_items: int = 0, blacklisted_genres: set = None) -> list[dict]:
    """Paginate through MangaDex and resolve details for each record."""
    all_records: list[dict] = []
    offset = 0
    limit = 100
    total_api = 0

    print("=" * 60)
    print("  MangaDex Fetcher — Korean & Chinese Manga")
    if max_items:
        print(f"  [TEST MODE] Will stop after {max_items} manga.")
    print("=" * 60)

    while True:
        print(f"\n  Fetching page at offset={offset} …")
        
        # Adjust limit for the last page in test mode
        current_limit = limit
        if max_items > 0 and (max_items - len(all_records)) < limit:
            current_limit = max_items - len(all_records)
            
        data = safe_get(f"{MANGADEX_BASE}/manga", params={
            "originalLanguage[]": ["ko", "zh"],
            "limit": current_limit,
            "offset": offset,
            "includes[]": ["cover_art", "author"],
            "order[followedCount]": "desc",
        })
        total_api += 1

        if not data or "data" not in data:
            print("  No data returned — stopping.")
            break

        items = data["data"]
        if not items:
            print("  Empty page — done paginating.")
            break

        for manga in items:
            manga_id = manga["id"]
            attrs = manga.get("attributes", {})
            rels = manga.get("relationships", [])

            # ── Title ──
            title = extract_title(attrs)
            alt_titles = extract_alt_titles(attrs)

            # ── Status ──
            status = attrs.get("status", "unknown")
            if status not in ("ongoing", "completed", "hiatus", "cancelled"):
                status = "ongoing"

            # ── Summary/Description ──
            summary = extract_summary(attrs)

            # ── Genres ──
            genres = extract_genres(attrs)
            
            if blacklisted_genres and any(str(g).strip().title() in blacklisted_genres for g in genres if g):
                continue


            # ── Rating & Statistics ──
            rating, rating_count, view_count = fetch_statistics(manga_id)
            total_api += 1

            # ── Author ──
            author_id = None
            for rel in rels:
                if rel.get("type") == "author":
                    author_id = rel.get("id")
                    break
            author = fetch_author_name(author_id) if author_id else None
            total_api += 1

            # ── Chapter count: prefer lastChapter attr, fall back to aggregate ──
            last_chapter = attrs.get("lastChapter")
            if last_chapter and last_chapter.isdigit():
                chapter_count = int(last_chapter)
            else:
                chapter_count = fetch_chapter_count(manga_id) or None
                total_api += 1

            # ── Cover image ──
            cover_id = None
            for rel in rels:
                if rel.get("type") == "cover_art":
                    cover_id = rel.get("id")
                    break
            cover_image = fetch_cover_url(manga_id, cover_id) if cover_id else None
            total_api += 1

            record = {
                "title": title,
                "author": author,
                "genres": genres,
                "chapter_count": chapter_count,
                "rating": rating,
                "rating_count": rating_count,
                "view_count": view_count,
                "status": status,
                "summary": summary,
                "source_site": "mangadex",
                "cover_image": cover_image,
                "external_id": manga_id,
                "mal_cross_id": str((attrs.get("links") or {}).get("mal")) if (attrs.get("links") or {}).get("mal") else None,
                "alt_titles": alt_titles,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            all_records.append(record)
            
            # Check if we hit the test mode limit
            if max_items > 0 and len(all_records) >= max_items:
                break

        processed = len(all_records)
        avg_calls = total_api // max(processed, 1)
        print(f"  ✓ {processed} manga processed so far | API calls: {total_api} | avg calls per manga: {avg_calls}")
        
        # Stop if we hit the limit
        if max_items > 0 and processed >= max_items:
            print("  Test mode limit reached.")
            break

        # Stop if we got fewer items than requested
        if len(items) < current_limit:
            print("  Last page reached.")
            break

        offset += limit

        # MangaDex hard caps offset at 10000
        if offset >= 10000:
            print("  MangaDex offset cap (10000) reached.")
            break

    return all_records


# ────────────────────────────────────────────────────────────
#  Supabase upsert
# ────────────────────────────────────────────────────────────

def upsert_to_supabase(records: list[dict]) -> int:
    """Upsert records in batches of 50 into manga_raw."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  ⚠ Supabase credentials not set — skipping upsert.")
        return 0    

    headers = supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/manga_raw?on_conflict=title,source_site"
    inserted = 0
    batch_size = 50

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        r = httpx.post(url, headers=headers, json=batch, timeout=30)
        if r.status_code in (200, 201):
            inserted += len(batch)
        else:
            print(f"  ⚠ Upsert batch {i//batch_size + 1} failed: {r.status_code}")
            print(f"    {r.text[:300]}")

    return inserted


# ────────────────────────────────────────────────────────────
#  Entry point
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    start = time.time()
    
    # Check for test mode
    max_items = 0
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        max_items = 10

    # Fetch
    import csv
    csv_path = os.path.join(os.path.dirname(__file__), "..", "genres_blacklist.csv")
    blacklisted_genres = set()
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                flag = (row.get("Blacklisted") or row.get("blacklisted") or "").strip().lower()
                genre = (row.get("Genre") or row.get("genre") or "").strip().title()
                if genre and flag in {"yes", "true", "1", "y"}:
                    blacklisted_genres.add(genre)

    records = fetch_all_manga(max_items=max_items, blacklisted_genres=blacklisted_genres)

    # Save to JSON
    json_path = os.path.join(os.path.dirname(__file__), "mangadex_raw.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"\n  💾 Saved {len(records)} records to {json_path}")

    # Upsert to Supabase
    upserted = upsert_to_supabase(records)
    print(f"  💾 Upserted {upserted} records to Supabase manga_raw")

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  DONE — {len(records)} total manga | {elapsed:.0f}s elapsed")
    print(f"  Author cache hits: {len(author_cache)} unique authors")
    print(f"  Cover cache hits:  {len(cover_cache)} unique covers")
    print(f"{'='*60}")

    client.close()
