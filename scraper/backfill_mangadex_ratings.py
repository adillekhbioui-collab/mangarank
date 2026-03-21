"""
Backfill script to patch MangaDex rankings and view counts into existing data.
Avoids making 40,000+ API calls by skipping author/chapter/cover lookups
and by batching the statistics endpoint.
"""

import os
import sys
import time
import httpx
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ── Load environment ────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MANGADEX_BASE = "https://api.mangadex.org"
DELAY = 0.5  # seconds between API calls

client = httpx.Client(timeout=30, follow_redirects=True)

def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

def safe_get(url: str, params: dict | None = None) -> dict | None:
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
    title_obj = attributes.get("title", {})
    if "en" in title_obj:
        return title_obj["en"]
    for alt in attributes.get("altTitles", []):
        if "en" in alt:
            return alt["en"]
    if title_obj:
        return next(iter(title_obj.values()))
    for alt in attributes.get("altTitles", []):
        if alt:
            return next(iter(alt.values()))
    return "Unknown Title"

def fetch_statistics_bulk(manga_ids: list[str]) -> dict:
    """Fetch rating data from MangaDex statistics endpoint for up to 100 IDs."""
    if not manga_ids:
        return {}
        
    url = f"{MANGADEX_BASE}/statistics/manga"
    
    # MangaDex statistics endpoint expects manga[] parameters
    # The normal httpx `params` doesn't handle list of strings like `manga[]=id1&manga[]=id2` reliably without correct configuration.
    # So we build the query string manually to be safe.
    query_string = "&".join([f"manga[]={mid}" for mid in manga_ids])
    full_url = f"{url}?{query_string}"
    
    data = safe_get(full_url)
    if not data or "statistics" not in data:
        return {}
        
    return data["statistics"]

def backfill():
    offset = 0
    limit = 100
    total_processed = 0
    total_patched = 0

    print("=" * 60)
    print("  MangaDex Backfill — Patching Ratings & View Counts")
    print("=" * 60)

    url_patch = f"{SUPABASE_URL}/rest/v1/manga_raw"
    headers = supabase_headers()

    while True:
        print(f"\n  Fetching page at offset={offset} …")
        data = safe_get(f"{MANGADEX_BASE}/manga", params={
            "originalLanguage[]": ["ko", "zh"],
            "limit": limit,
            "offset": offset,
            "order[followedCount]": "desc",
        })

        if not data or "data" not in data:
            print("  No data returned — stopping.")
            break

        items = data["data"]
        if not items:
            print("  Empty page — done paginating.")
            break

        # Extract IDs and titles
        id_to_title = {manga["id"]: extract_title(manga.get("attributes", {})) for manga in items}
        manga_ids = list(id_to_title.keys())

        # Bulk fetch statistics for these 100 mangas (1 API call)
        stats = fetch_statistics_bulk(manga_ids)

        # Patch Supabase records
        batch_patched = 0
        for manga_id, title in id_to_title.items():
            manga_stats = stats.get(manga_id, {})
            rating_obj = manga_stats.get("rating", {})
            
            raw_score = rating_obj.get("bayesian") or rating_obj.get("average")
            if raw_score is None:
                continue # Skip if there's absolutely no rating data

            normalized_score = round(float(raw_score) * 10, 2)
            distribution = rating_obj.get("distribution", {})
            total_votes = sum(distribution.values()) if distribution else None
            follows = manga_stats.get("follows", None)

            # Update existing row in Supabase using the title as the identifier
            patch_data = {
                "rating": normalized_score,
                "rating_count": total_votes,
                "view_count": follows
            }
            
            patch_url = f"{url_patch}?source_site=eq.mangadex&title=eq.{title}"
            
            # Simple retry specifically for the client.patch hitting Supabase
            for patch_attempt in range(3):
                try:
                    r = client.patch(patch_url, headers=headers, json=patch_data)
                    if r.status_code in (200, 204, 201):
                        batch_patched += 1
                    else:
                        print(f"    ⚠ Failed to patch '{title}': {r.status_code} - {r.text[:200]}")
                    break # Success or non-network error, break out of retry loop
                except httpx.HTTPError as e:
                    print(f"    ⚠ Network error patching '{title}' on attempt {patch_attempt+1}: {e}")
                    time.sleep(2)

        total_processed += len(items)
        total_patched += batch_patched
        print(f"  ✓ Processed {total_processed} items. Successfully patched {batch_patched} this batch.")

        if len(items) < limit:
            break

        offset += limit
        if offset >= 10000:
            print("  MangaDex offset cap (10000) reached.")
            break

    print(f"\n  DONE! Processed {total_processed} manga and successfully patched {total_patched} database rows.")

if __name__ == "__main__":
    start = time.time()
    backfill()
    print(f"  Elapsed: {time.time() - start:.0f}s")
