"""
Step 5 — Fetch manhwa & manhua data from the Kitsu API.

Runs two sequential loops (manhwa then manhua), streaming
results to JSON and upserting page-by-page into Supabase.
Genre URLs are cached across both loops to minimize API calls.
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

KITSU_BASE = "https://kitsu.io/api/edge/manga"
DELAY = 0.6  # seconds between API calls
SUBTYPES = ["manhwa", "manhua"]

# ── Genre cache (shared across both subtypes) ───────────────
genre_cache: dict[str, list[str]] = {}  # genre_url -> [genre names]

# ── HTTP client ─────────────────────────────────────────────
client = httpx.Client(
    timeout=30,
    follow_redirects=True,
    headers={"Accept": "application/vnd.api+json", "Content-Type": "application/vnd.api+json"},
)


def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
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
            print(f"    ⚠ {url[:80]} returned {r.status_code}")
            return None
        except (httpx.HTTPError, httpx.ConnectError, Exception) as e:
            print(f"    ⚠ Error on attempt {attempt+1}: {e}")
            time.sleep(2)
    return None


def fetch_genres(genre_url: str) -> list[str]:
    """Fetch genre names from a Kitsu genre relationship URL, with caching."""
    if not genre_url:
        return []

    if genre_url in genre_cache:
        return genre_cache[genre_url]

    data = safe_get(genre_url)
    if not data or "data" not in data:
        genre_cache[genre_url] = []
        return []

    names = []
    for g in data["data"]:
        name = g.get("attributes", {}).get("name")
        if name:
            names.append(name)

    genre_cache[genre_url] = names
    return names


def parse_kitsu_rating(attrs: dict) -> float | None:
    """
    Parse Kitsu rating into 0-100 scale with fallbacks.
    Order:
    1) averageRating
    2) bayesianRating
    3) derived from ratingFrequencies
    """
    for key in ("averageRating", "bayesianRating"):
        raw = attrs.get(key)
        if raw is None:
            continue
        try:
            return max(0.0, min(100.0, float(raw)))
        except (TypeError, ValueError):
            pass

    freqs = attrs.get("ratingFrequencies") or {}
    if not isinstance(freqs, dict):
        return None

    weighted = 0.0
    total = 0
    for bucket_raw, count_raw in freqs.items():
        try:
            bucket = int(str(bucket_raw))
            count = int(count_raw)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        # Kitsu buckets are typically 1..20 (half-stars).
        # Convert to 0-100 by multiplying bucket by 5.
        weighted += (bucket * 5.0) * count
        total += count

    if total <= 0:
        return None

    return max(0.0, min(100.0, weighted / total))


def parse_kitsu_rating_count(attrs: dict) -> int:
    """
    Prefer ratingCount; fallback to sum(ratingFrequencies); then userCount.
    """
    raw_count = attrs.get("ratingCount")
    if raw_count is not None:
        try:
            return max(0, int(raw_count))
        except (TypeError, ValueError):
            pass

    freqs = attrs.get("ratingFrequencies") or {}
    if isinstance(freqs, dict):
        total = 0
        for value in freqs.values():
            try:
                total += int(value)
            except (TypeError, ValueError):
                pass
        if total > 0:
            return total

    fallback = attrs.get("userCount", 0) or 0
    try:
        return max(0, int(fallback))
    except (TypeError, ValueError):
        return 0


# ────────────────────────────────────────────────────────────
#  Supabase upsert
# ────────────────────────────────────────────────────────────

def upsert_to_supabase(records: list[dict]) -> int:
    """Upsert records into manga_raw and return number inserted."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("    ⚠ Supabase credentials not set — skipping upsert.")
        return 0

    if not records:
        return 0

    headers = supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/manga_raw?on_conflict=title,source_site"

    r = httpx.post(url, headers=headers, json=records, timeout=30)
    if r.status_code in (200, 201, 204):
        return len(records)

    print(f"    ⚠ Upsert failed: {r.status_code}")
    print(f"      {r.text[:300]}")
    return 0


# ────────────────────────────────────────────────────────────
#  Main fetch loop
# ────────────────────────────────────────────────────────────

def fetch_and_stream(test_mode: bool = False, blacklisted_genres: set = None):
    """
    Loop over both subtypes (manhwa, manhua), paginate through Kitsu,
    stream to JSON, upsert page-by-page, and free memory each page.
    """
    grand_total = 0
    test_limit = 40 if test_mode else 0

    json_path = os.path.join(os.path.dirname(__file__), "kitsu_raw.json")

    print("=" * 60)
    print("  Kitsu Fetcher — Manhwa & Manhua")
    if test_mode:
        print(f"  [TEST MODE] Will stop after {test_limit} total records.")
    print("=" * 60)

    try:
        f = open(json_path, "w", encoding="utf-8")
        f.write("[\n")
        first_record_written = False

        for subtype in SUBTYPES:
            print(f"\n{'─'*60}")
            print(f"  Fetching subtype: {subtype}")
            print(f"{'─'*60}")

            offset = 0
            subtype_total = 0

            while True:
                # Check test mode limit
                if test_limit > 0 and grand_total >= test_limit:
                    print(f"  Test mode limit ({test_limit}) reached.")
                    break

                print(f"\n  [{subtype}] offset={offset} …")

                data = safe_get(KITSU_BASE, params={
                    f"filter[subtype]": subtype,
                    "page[limit]": 20,
                    "page[offset]": offset,
                    "sort": "-userCount",
                })

                if not data or "data" not in data:
                    print("  No data returned — stopping this subtype.")
                    break

                items = data["data"]
                if not items:
                    print("  Empty page — done with this subtype.")
                    break

                page_records: list[dict] = []

                for item in items:
                    # Check test mode limit per-record
                    if test_limit > 0 and grand_total >= test_limit:
                        break

                    attrs = item.get("attributes", {})
                    rels = item.get("relationships", {})

                    # ── Title (skip if missing) ──
                    title = attrs.get("canonicalTitle")
                    if not title or not title.strip():
                        continue

                    # ── Alternative titles / IDs ──
                    titles_obj = attrs.get("titles", {}) or {}
                    alt_titles = []
                    seen_alt = set()
                    for value in titles_obj.values():
                        if not isinstance(value, str):
                            continue
                        clean_value = value.strip()
                        if not clean_value:
                            continue
                        if clean_value.lower() == title.strip().lower():
                            continue
                        key = clean_value.lower()
                        if key in seen_alt:
                            continue
                        seen_alt.add(key)
                        alt_titles.append(clean_value)

                    # ── Summary/Synopsis ──
                    summary = attrs.get("synopsis")

                    # ── Status ──
                    raw_status = attrs.get("status", "")
                    status = "completed" if raw_status == "finished" else "ongoing"

                    # ── Rating (0-100 scale with fallback parsing) ──
                    rating = parse_kitsu_rating(attrs)

                    # ── Rating count & view count ──
                    rating_count = parse_kitsu_rating_count(attrs)
                    popularity_rank = attrs.get("popularityRank")
                    view_count = max(0, 100000 - popularity_rank) if popularity_rank else 0

                    # ── Chapter count (keep None for ongoing/unknown) ──
                    chapter_count = attrs.get("chapterCount") or None

                    # ── Cover image ──
                    cover_image = None
                    poster = attrs.get("posterImage")
                    if poster:
                        cover_image = poster.get("large") or poster.get("medium")

                    # ── Genres (cached fetch) ──
                    genre_url = None
                    genre_rel = rels.get("genres", {})
                    if genre_rel:
                        links = genre_rel.get("links", {})
                        genre_url = links.get("related")
                    genres = fetch_genres(genre_url) if genre_url else []

                    if blacklisted_genres and any(str(g).strip().title() in blacklisted_genres for g in genres if g):
                        continue

                    # ── Author (Kitsu staff is unreliable, leave null) ──
                    author = None

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
                        "source_site": "kitsu",
                        "cover_image": cover_image,
                        "external_id": item.get("id"),
                        "alt_titles": alt_titles,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }

                    page_records.append(record)
                    grand_total += 1

                    # Stream to JSON file incrementally
                    if first_record_written:
                        f.write(",\n")
                    json.dump(record, f, ensure_ascii=False, indent=2)
                    first_record_written = True

                # ── Upsert page to Supabase ──
                upserted = upsert_to_supabase(page_records)
                subtype_total += len(page_records)

                print(
                    f"  ✓ [{subtype}] offset={offset} | "
                    f"Upserted: {upserted} | "
                    f"Subtype total: {subtype_total} | "
                    f"Grand total: {grand_total} | "
                    f"Genre cache: {len(genre_cache)}"
                )

                # ── Free memory immediately ──
                page_records = []

                # Check test mode
                if test_limit > 0 and grand_total >= test_limit:
                    break

                # Check if there is a next page
                next_link = data.get("links", {}).get("next")
                if not next_link:
                    print(f"  No next link — done with {subtype}.")
                    break

                offset += 20

    finally:
        if "f" in locals() and not f.closed:
            f.write("\n]\n")
            f.close()
            print(f"\n  💾 Closed JSON file at {json_path}")

    return grand_total


# ────────────────────────────────────────────────────────────
#  Entry point
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    start = time.time()

    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"

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

    total = fetch_and_stream(test_mode=test_mode, blacklisted_genres=blacklisted_genres)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  DONE — {total} total records | {elapsed:.0f}s elapsed")
    print(f"  Genre cache: {len(genre_cache)} unique URLs cached")
    print(f"{'='*60}")

    client.close()
