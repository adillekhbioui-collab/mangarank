
"""
Script to backfill missing summaries in the manga_rankings table.
Queries Supabase for records where summary is missing (or null) and uses the AniList GraphQL API to fetch the description by searching for the exact title.
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
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ANILIST_URL = "https://graphql.anilist.co"
DELAY = 1.0  # to stay under 90 req/min

client = httpx.Client(timeout=30, follow_redirects=True)

GRAPHQL_SEARCH_QUERY = """
query ($search: String) {
  Media(search: $search, type: MANGA) {
    title { english romaji }
    description(asHtml: false)
  }
}
"""

def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

def get_missing_summaries() -> list[dict]:
    """Fetch manga from manga_rankings where summary is null."""
    headers = supabase_headers()
    # PostgREST syntax for is null
    url = f"{SUPABASE_URL}/rest/v1/manga_rankings?select=id,title&summary=is.null"
    r = client.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print(f"Failed to fetch missing summaries: {r.status_code} {r.text}")
        return []

def update_summary(manga_id: int, summary: str):
    """Update the summary for a specific row in manga_rankings."""
    headers = supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/manga_rankings?id=eq.{manga_id}"
    payload = {"summary": summary}
    r = client.patch(url, headers=headers, json=payload)
    if r.status_code not in (200, 204):
        print(f"Failed to update manga id {manga_id}: {r.status_code} {r.text}")

def fetch_anilist_description(title: str) -> str | None:
    """Search AniList by title and return description if found."""
    payload = {
        "query": GRAPHQL_SEARCH_QUERY,
        "variables": {"search": title}
    }
    
    for attempt in range(3):
        try:
            time.sleep(DELAY)
            r = client.post(ANILIST_URL, json=payload)
            if r.status_code == 200:
                data = r.json()
                media = data.get("data", {}).get("Media")
                if media:
                    return media.get("description")
                return None
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", 5))
                time.sleep(wait)
                continue
            if r.status_code == 404:
                # Not found on AniList
                return None
            print(f"    ⚠ AniList returned {r.status_code} for '{title}'")
            return None
        except httpx.HTTPError as e:
            print(f"    ⚠ HTTP error for '{title}' on attempt {attempt+1}: {e}")
            time.sleep(2)
    return None

def main(test_mode: bool = False):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    print("Fetching missing summaries from Supabase...")
    missing = get_missing_summaries()
    print(f"Found {len(missing)} manga without summaries.")
    
    if test_mode and missing:
        missing = missing[:5]
        print(f"[TEST MODE] limiting to {len(missing)} manga.")

    processed = 0
    updated = 0

    for manga in missing:
        manga_id = manga["id"]
        title = manga["title"]
        print(f"[{processed+1}/{len(missing)}] Searching AniList for: {title}")
        
        description = fetch_anilist_description(title)
        if description:
            print("  ✓ Found description! Updating Supabase...")
            update_summary(manga_id, description)
            updated += 1
        else:
            print("  ✗ No description found.")
            
        processed += 1

    print(f"\nDone! Processed {processed} manga, updated {updated} summaries.")

if __name__ == "__main__":
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"
    main(test_mode=test_mode)
