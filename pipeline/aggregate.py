"""
Step 9 — Scoring and Aggregation Pipeline.

Reads pipeline/deduplicated.json, computes a weighted aggregated
score per manga using site weights and log-confidence, then
upserts results into the Supabase manga_rankings table.
"""

import os
import sys
import json
import math
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

# ── Site weights (adjust here without touching other code) ──
SITE_WEIGHTS = {
    "anilist":  1.0,
    "mal":      0.95,
    "mangadex": 0.85,
    "kitsu":    0.7,
}

POPULARITY_WEIGHTS = {
    "anilist":  1.0,
    "mal":      0.95,
    "mangadex": 0.85,
    "kitsu":    0.0,
}


def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


# ────────────────────────────────────────────────────────────
#  Scoring logic
# ────────────────────────────────────────────────────────────

def compute_score(source_ratings: list[dict]) -> float | None:
    """
    Weighted score using log-confidence.
      confidence = log(rating_count + 1)  (or 0.5 if rating_count is 0/unknown)
      score = Σ(rating × weight × confidence) / Σ(weight × confidence)
    """
    numerator = 0.0
    denominator = 0.0

    for sr in source_ratings:
        rating = sr.get("rating")
        if rating is None:
            continue

        source = sr.get("source_site", "")
        weight = SITE_WEIGHTS.get(source, 0.5)

        rating_count = sr.get("rating_count", 0) or 0
        if rating_count > 0:
            confidence = math.log(rating_count + 1)
        else:
            confidence = 0.5

        numerator += rating * weight * confidence
        denominator += weight * confidence

    if denominator == 0:
        return None

    return round(numerator / denominator, 2)


def compute_total_views(source_ratings: list[dict]) -> int:
    """
    Compute total views by strictly summing real raw hits from all valid platforms.
    Ignore Kitsu view_count as it is an inverted rank.
    """
    total = 0
    for sr in source_ratings:
        source = sr.get("source_site")
        if source == "kitsu":
            continue
        views = sr.get("view_count", 0) or 0
        total += views
    return total

def compute_popularity_score(source_ratings: list[dict], max_views_map: dict[str, int]) -> float | None:
    """
    Compute normalized popularity score with log-confidence.
    formula: popularity_score = [ Σ (P_s × W_s × log(v_s + 1)) / Σ (W_s × log(V_{s,max} + 1)) ] × 100
    where P_s = v_s / V_{s,max}
    """
    numerator = 0.0
    denominator = 0.0

    views_by_source: dict[str, int] = {}
    for sr in source_ratings:
        source = sr.get("source_site", "")
        views = sr.get("view_count", 0) or 0
        if views > 0:
            views_by_source[source] = views

    for source, weight in POPULARITY_WEIGHTS.items():
        if weight == 0:
            continue

        max_v = max_views_map.get(source, 1)
        if max_v <= 0:
            continue

        views = views_by_source.get(source, 0)

        normalizer = math.log(max_v + 1)
        denominator += weight * normalizer

        if views <= 0:
            continue

        p_s = views / max_v
        confidence = math.log(views + 1)
        numerator += p_s * weight * confidence

    if denominator <= 0:
        return 0.0

    return round((numerator / denominator) * 100, 2)


def compute_best_summary(source_ratings: list[dict]) -> str | None:
    """
    Finds the longest non-null summary from all available sources.
    """
    best_summary = None
    max_length = 0
    for sr in source_ratings:
        summary = sr.get("summary")
        if summary and isinstance(summary, str):
            length = len(summary.strip())
            if length > max_length:
                best_summary = summary.strip()
                max_length = length
    return best_summary


# ────────────────────────────────────────────────────────────
#  Build ranking records
# ────────────────────────────────────────────────────────────

def build_rankings(deduplicated: list[dict]) -> list[dict]:
    """Build manga_rankings records from deduplicated data."""
    rankings = []
    now = datetime.now(timezone.utc).isoformat()
    
    # ── First Pass: Find max_views per platform ──
    max_views_map = {"anilist": 0, "mal": 0, "mangadex": 0, "kitsu": 0}
    for manga in deduplicated:
        for sr in manga.get("source_ratings", []):
            source = sr.get("source_site", "")
            views = sr.get("view_count", 0) or 0
            if source in max_views_map and views > max_views_map[source]:
                max_views_map[source] = views

    print(f"\n  Max views by source: {max_views_map}")

    # ── Second Pass: Build ranking records ──
    for manga in deduplicated:
        source_ratings = manga.get("source_ratings", [])

        aggregated_score = compute_score(source_ratings)
        total_views = compute_total_views(source_ratings)
        popularity_score = compute_popularity_score(source_ratings, max_views_map)
        best_summary = compute_best_summary(source_ratings)

        # ── Completion Rate Logic ──
        completion_rate = None
        total_readers = 0
        
        for sr in source_ratings:
            if sr.get("source_site") == "anilist":
                completed = sr.get("count_completed", 0)
                dropped   = sr.get("count_dropped", 0)
                current   = sr.get("count_current", 0)
                paused    = sr.get("count_paused", 0)
                
                total_readers = completed + dropped + current + paused
                
                if total_readers >= 1000:
                    completion_rate = round((completed / total_readers) * 100, 1)
                break

        record = {
            "title": manga["title"],
            "author": manga.get("author"),
            "genres": manga.get("genres", []),
            "alt_titles": manga.get("alt_titles", []),
            "chapter_count": manga.get("chapter_count") or 0,
            "aggregated_score": aggregated_score,
            "popularity_score": popularity_score,
            "total_views": total_views,
            "summary": best_summary,
            "status": manga.get("status", "ongoing"),
            "cover_image": manga.get("cover_image"),
            "completion_rate": completion_rate,
            "total_readers": total_readers,
            "updated_at": now,
        }
        rankings.append(record)

    return rankings


# ────────────────────────────────────────────────────────────
#  Supabase upsert
# ────────────────────────────────────────────────────────────

def upsert_to_supabase(records: list[dict]) -> int:
    """Upsert records in batches of 50 into manga_rankings."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  ⚠ Supabase credentials not set — skipping upsert.")
        return 0

    headers = supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/manga_rankings?on_conflict=title"
    inserted = 0
    batch_size = 500

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        r = httpx.post(url, headers=headers, json=batch, timeout=30)
        if r.status_code in (200, 201, 204):
            inserted += len(batch)
        else:
            print(f"  ⚠ Upsert batch {i//batch_size + 1} failed: {r.status_code}")
            print(f"    {r.text[:300]}")

        if (i // batch_size + 1) % 50 == 0:
            print(f"    … upserted {inserted} records so far")

    return inserted


# ────────────────────────────────────────────────────────────
#  Top 10 preview table
# ────────────────────────────────────────────────────────────

def print_top10(rankings: list[dict]):
    """Print the top 10 manga by aggregated_score as a preview."""
    # Filter out records with no score, then sort descending
    scored = [r for r in rankings if r["aggregated_score"] is not None]
    scored.sort(key=lambda r: r["aggregated_score"], reverse=True)

    top10 = scored[:10]

    print(f"\n  {'Rank':<5} {'Score':<8} {'Views':<10} {'Title'}")
    print(f"  {'─'*5} {'─'*8} {'─'*10} {'─'*40}")
    for i, r in enumerate(top10, 1):
        title = r["title"][:40]
        print(f"  {i:<5} {r['aggregated_score']:<8} {r['total_views']:<10} {title}")


def print_completion_breakdown(rankings: list[dict]):
    """Print breakdown of completion rates."""
    valid = [r for r in rankings if r["completion_rate"] is not None]
    nulls = [r for r in rankings if r["completion_rate"] is None]
    
    no_anilist = sum(1 for r in nulls if r["total_readers"] == 0)
    not_enough_readers = sum(1 for r in nulls if r["total_readers"] > 0 and r["total_readers"] < 1000)

    print(f"\n  COMPLETION RATE BREAKDOWN")
    print(f"  {'─'*60}")
    print(f"  Total with completion data: {len(valid)}")
    print(f"  Total without data:         {len(nulls)}")
    print(f"    - No AniList data:        {no_anilist}")
    print(f"    - < 1000 readers:         {not_enough_readers}")
    
    if valid:
        valid.sort(key=lambda r: r["completion_rate"], reverse=True)
        top5 = valid[:5]
        bottom5 = valid[-5:]
        
        print(f"\n  Top 5 by Completion Rate:")
        for i, r in enumerate(top5, 1):
            print(f"    {i}. {r['completion_rate']}% - {r['title'][:40]} ({r['total_readers']} readers)")
            
        print(f"\n  Bottom 5 by Completion Rate:")
        for i, r in enumerate(bottom5, 1):
            print(f"    {i}. {r['completion_rate']}% - {r['title'][:40]} ({r['total_readers']} readers)")


def print_popularity_debug(rankings: list[dict]):
    """Print popularity-focused debug views for validation."""
    by_popularity = sorted(
        rankings,
        key=lambda r: (r.get("popularity_score") or 0.0),
        reverse=True,
    )

    print(f"\n  Top 20 by Popularity Score")
    print(f"  {'─'*92}")
    print(f"  {'Rank':<5} {'Popularity':<11} {'Views':<10} {'Title'}")
    print(f"  {'─'*5} {'─'*11} {'─'*10} {'─'*60}")

    for i, r in enumerate(by_popularity[:20], 1):
        title = (r.get("title") or "")[:60]
        popularity = r.get("popularity_score") or 0.0
        total_views = r.get("total_views") or 0
        print(f"  {i:<5} {popularity:<11} {total_views:<10} {title}")

    targets = {
        "solo leveling",
        "omniscient reader",
        "star martial god technique",
    }
    rank_map: dict[str, tuple[int, dict]] = {}
    for i, r in enumerate(by_popularity, 1):
        title = (r.get("title") or "").strip().lower()
        rank_map[title] = (i, r)

    print(f"\n  Popularity sanity check (problematic titles)")
    print(f"  {'─'*92}")
    print(f"  {'Title':<35} {'Views':<10} {'Popularity':<11} {'Rank':<6}")
    print(f"  {'─'*35} {'─'*10} {'─'*11} {'─'*6}")

    for target in targets:
        match = None
        for title_key, payload in rank_map.items():
            if target in title_key:
                match = payload
                break
        if match is None:
            print(f"  {target:<35} {'N/A':<10} {'N/A':<11} {'N/A':<6}")
            continue

        rank, record = match
        display_title = (record.get("title") or "")[:35]
        total_views = record.get("total_views") or 0
        popularity = record.get("popularity_score") or 0.0
        print(f"  {display_title:<35} {total_views:<10} {popularity:<11} {rank:<6}")


# ────────────────────────────────────────────────────────────
#  Entry point
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(__file__), "deduplicated.json")

    print("=" * 60)
    print("  Scoring & Aggregation Pipeline")
    print("=" * 60)

    # Load
    print("\n  Loading deduplicated.json …")
    with open(input_path, "r", encoding="utf-8") as f:
        deduplicated = json.load(f)
    print(f"  ✓ Loaded {len(deduplicated)} unique manga")

    # Score
    print("\n  Computing weighted scores & completion rates …")
    rankings = build_rankings(deduplicated)

    scored_count = sum(1 for r in rankings if r["aggregated_score"] is not None)
    unscored = len(rankings) - scored_count
    print(f"  ✓ {scored_count} manga scored, {unscored} have no rating data")

    # Upsert
    print("\n  Upserting to manga_rankings …")
    upserted = upsert_to_supabase(rankings)
    print(f"  ✓ Upserted {upserted} records to manga_rankings")

    # Top 10 preview
    print_top10(rankings)
    
    # Completion Rate breakdown
    print_completion_breakdown(rankings)

    # Popularity debug checks
    print_popularity_debug(rankings)

    # Summary
    print(f"\n{'='*60}")
    print(f"  AGGREGATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Total manga written:     {upserted}")
    print(f"  Scored manga:            {scored_count}")
    print(f"  Unscored (no ratings):   {unscored}")
    print(f"{'='*60}")
