"""
backend/constants.py

Module-level constants and pure utility functions shared across the backend.
No FastAPI imports — safe to import from any module without circular dependencies.
"""

import os
import csv


# ── Sort-by mapping ──────────────────────────────────────────
SORT_MAP = {
    "score": "aggregated_score",
    "views": "popularity_score",
    "chapters": "chapter_count",
    "completion": "completion_rate",
}

# ── Columns we actually need on the list endpoint ────────────
MANGA_COLS = (
    "title,author,genres,alt_titles,chapter_count,aggregated_score,"
    "total_views,popularity_score,status,cover_image,summary,"
    "completion_rate,total_readers"
)

# ── Category → filter mapping for /top/{category} ────────────
GENRE_CATEGORIES = {
    "action", "romance", "fantasy", "drama",
    "thriller", "supernatural",
}
STATUS_CATEGORIES = {"completed", "ongoing"}

# ── Allowed analytics event types ────────────────────────────
ANALYTICS_EVENT_TYPES = {
    "search",
    "manga_click",
    "manga_view",
    "filter_applied",
    "watchlist_add",
    "watchlist_remove",
    "filter_genre",
    "filter_status",
    "filter_sort",
    "category_view",
    "genre_network_click",
}

# ── File paths ───────────────────────────────────────────────
_BACKEND_DIR = os.path.dirname(__file__)

BLACKLIST_CSV_PATH = os.path.join(_BACKEND_DIR, "..", "genres_blacklist.csv")

IMAGE_CACHE_DIR = os.path.join(_BACKEND_DIR, "..", ".cache", "images")
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)


# ── Pure utility: genre blacklist loader ─────────────────────

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
