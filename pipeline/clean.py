"""
Step 7 — Data Cleaning Pipeline.

Reads all records from the Supabase manga_raw table and applies:
  - whitespace stripping on text fields
  - chapter_count normalization to non-negative int
  - genre title-casing
  - removal of records with empty titles
  - rating normalization to 0–100 scale per source
  - null fixing for view_count and rating_count
  - status normalization

Saves cleaned data to pipeline/cleaned.json.
"""

import os
import sys
import json
import httpx
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ── Load environment ────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


# ────────────────────────────────────────────────────────────
#  Fetch all raw records from Supabase
# ────────────────────────────────────────────────────────────

def fetch_all_raw() -> list[dict]:
    """
    Fetch all rows from manga_raw using pagination (Supabase
    returns max 1000 per request by default).
    """
    headers = supabase_headers()
    headers["Prefer"] = "count=exact"
    all_records = []
    offset = 0
    page_size = 1000

    print("  Fetching records from manga_raw …")

    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/manga_raw"
            f"?select=*"
            f"&order=id.asc"
            f"&offset={offset}"
            f"&limit={page_size}"
        )
        r = httpx.get(url, headers=headers, timeout=30)

        if r.status_code not in (200, 206):
            print(f"  ⚠ Fetch failed at offset {offset}: {r.status_code}")
            print(f"    {r.text[:300]}")
            break

        rows = r.json()
        if not rows:
            break

        all_records.extend(rows)
        print(f"    Fetched {len(all_records)} so far …")

        if len(rows) < page_size:
            break

        offset += page_size

    print(f"  ✓ Total raw records fetched: {len(all_records)}")
    return all_records


# ────────────────────────────────────────────────────────────
#  Cleaning logic
# ────────────────────────────────────────────────────────────

def clean_records(raw: list[dict]) -> tuple[list[dict], dict]:
    """
    Apply all cleaning rules to the raw records.
    Returns (cleaned_records, stats_dict).
    """
    stats = {
        "total_input": len(raw),
        "removed_empty_title": 0,
        "ratings_normalized": 0,
        "nulls_fixed": 0,
        "total_output": 0,
    }

    cleaned = []

    for rec in raw:
        # ── 1. Strip whitespace from text fields ──
        title = (rec.get("title") or "").strip()
        author = (rec.get("author") or "").strip() or None
        genres = rec.get("genres") or []
        if isinstance(genres, list):
            genres = [g.strip() for g in genres if isinstance(g, str) and g.strip()]
        else:
            genres = []

        # ── 4. Remove records with empty title ──
        if not title:
            stats["removed_empty_title"] += 1
            continue

        # ── 3. Normalize genres to title case ──
        genres = [g.title() for g in genres]

        # ── 2. Convert chapter_count to non-negative int ──
        chapter_count = rec.get("chapter_count")
        try:
            chapter_count = int(chapter_count)
            if chapter_count < 0:
                chapter_count = 0
        except (TypeError, ValueError):
            chapter_count = 0

        # ── 5. Normalize rating to 0–100 scale ──
        rating = rec.get("rating")
        source = rec.get("source_site", "")

        if rating is not None:
            try:
                rating = float(rating)

                if source == "mangadex":
                    # MangaDex: 0–10 scale → multiply by 10
                    rating = rating * 10
                    stats["ratings_normalized"] += 1
                elif source == "anilist":
                    # AniList: already 0–100, use as-is
                    stats["ratings_normalized"] += 1
                elif source == "kitsu":
                    # Kitsu: already 0–100 as float, use as-is
                    stats["ratings_normalized"] += 1

                # Clamp to [0, 100]
                rating = max(0.0, min(100.0, rating))

            except (TypeError, ValueError):
                rating = None

        # ── 6. Fix null view_count and rating_count ──
        view_count = rec.get("view_count")
        rating_count = rec.get("rating_count")

        if view_count is None:
            view_count = 0
            stats["nulls_fixed"] += 1
        else:
            try:
                view_count = int(view_count)
            except (TypeError, ValueError):
                view_count = 0
                stats["nulls_fixed"] += 1

        if rating_count is None:
            rating_count = 0
            stats["nulls_fixed"] += 1
        else:
            try:
                rating_count = int(rating_count)
            except (TypeError, ValueError):
                rating_count = 0
                stats["nulls_fixed"] += 1

        # ── 7. Normalize status ──
        status = rec.get("status", "")
        if status != "completed":
            status = "ongoing"

        # ── 8. Clean summary ──
        summary = (rec.get("summary") or "").strip() or None

        # ── 9. Preserve cross-source identity fields ──
        external_id = (rec.get("external_id") or "").strip() or None
        mal_cross_id = (rec.get("mal_cross_id") or "").strip() or None
        raw_alt_titles = rec.get("alt_titles") or []
        if not isinstance(raw_alt_titles, list):
            raw_alt_titles = []
        alt_titles = []
        seen_alt_titles = set()
        for alt in raw_alt_titles:
            if not isinstance(alt, str):
                continue
            clean_alt = alt.strip()
            if not clean_alt:
                continue
            key = clean_alt.lower()
            if key in seen_alt_titles:
                continue
            seen_alt_titles.add(key)
            alt_titles.append(clean_alt)

        raw_cross_link_ids = rec.get("cross_link_ids") or []
        if not isinstance(raw_cross_link_ids, list):
            raw_cross_link_ids = []
        cross_link_ids = []
        seen_cross_link_ids = set()
        for token in raw_cross_link_ids:
            if not isinstance(token, str):
                continue
            clean_token = token.strip().lower()
            if not clean_token:
                continue
            if clean_token in seen_cross_link_ids:
                continue
            seen_cross_link_ids.add(clean_token)
            cross_link_ids.append(clean_token)

        # ── Build cleaned record ──
        cleaned_rec = {
            "title": title,
            "author": author,
            "genres": genres,
            "chapter_count": chapter_count,
            "rating": rating,
            "rating_count": rating_count,
            "view_count": view_count,
            "status": status,
            "source_site": source,
            "cover_image": rec.get("cover_image"),
            "fetched_at": rec.get("fetched_at"),
            "summary": summary,
            "count_current": rec.get("count_current", 0),
            "count_completed": rec.get("count_completed", 0),
            "count_dropped": rec.get("count_dropped", 0),
            "count_paused": rec.get("count_paused", 0),
            "count_planning": rec.get("count_planning", 0),
            "external_id": external_id,
            "mal_cross_id": mal_cross_id,
            "alt_titles": alt_titles,
            "cross_link_ids": cross_link_ids,
        }

        # ── 10. Filter Blacklisted Genres ──
        if any(str(g).strip().title() in blacklisted_genres for g in genres if g):
            stats.setdefault("removed_blacklisted", 0)
            stats["removed_blacklisted"] += 1
            continue

        cleaned.append(cleaned_rec)

    stats["total_output"] = len(cleaned)
    return cleaned, stats


# ────────────────────────────────────────────────────────────
#  Entry point
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    print("=" * 60)
    print("  Data Cleaning Pipeline")
    print("=" * 60)

    # Fetch
    raw = fetch_all_raw()

    if not raw:
        print("  No records found in manga_raw. Run the fetchers first.")
        sys.exit(1)

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

    # Clean
    print("\n  Cleaning records …")
    cleaned, stats = clean_records(raw, blacklisted_genres)

    # Save to JSON
    json_path = os.path.join(os.path.dirname(__file__), "cleaned.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"  CLEANING SUMMARY")
    print(f"{'='*60}")
    print(f"  Total input records:      {stats['total_input']}")
    print(f"  Removed (empty title):    {stats['removed_empty_title']}")
    print(f"  Ratings normalized:       {stats['ratings_normalized']}")
    print(f"  Null fields fixed:        {stats['nulls_fixed']}")
    print(f"  Total output records:     {stats['total_output']}")
    print(f"  Saved to: {json_path}")
    print(f"{'='*60}")
