"""
Step 4 — Fetch manhwa & manhua data from the AniList GraphQL API.

Paginates through all Korean (KR) and Chinese (CN) manga using
a GraphQL query. Implements a stream-and-flush pattern for memory
optimization and incremental JSON saving. Upserts every batch into
the Supabase manga_raw table with source_site = 'anilist'.
"""

import os
import sys
import json
import time
import re
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

ANILIST_URL = "https://graphql.anilist.co"
DELAY = 1.2  # to stay under 90 req/min

# ── GraphQL Query ───────────────────────────────────────────
GRAPHQL_QUERY = """
query ($page: Int, $country: CountryCode) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage currentPage total }
    media(
      type: MANGA,
      countryOfOrigin: $country,
      sort: POPULARITY_DESC
    ) {
            id
            idMal
      title { english romaji }
            synonyms
      status
      genres
      description(asHtml: false)
      averageScore
    meanScore
      popularity
            externalLinks {
                url
                site
            }
      chapters
      coverImage { large }
      staff {
        edges {
          node { name { full } }
          role
        }
      }
      stats {
        statusDistribution {
          status
          amount
        }
      }
    }
  }
}
"""

COUNTRIES = ["KR", "CN"]
RESUME_COUNTRY = "KR"   # change to "CN" once KR finishes
RESUME_PAGE    = 1    # page to start from for the resume country # Korean manhwa + Chinese manhua
RESUME_STATE_PATH = os.path.join(os.path.dirname(__file__), "anilist_resume_state.json")

# ── HTTP client ─────────────────────────────────────────────
client = httpx.Client(timeout=30, follow_redirects=True)

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

def safe_post(url: str, json_data: dict) -> dict | None:
    """POST with retry (up to 3 attempts) and rate-limit delay."""
    for attempt in range(3):
        try:
            time.sleep(DELAY)
            r = client.post(url, json=json_data)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", 5))
                print(f"    Rate-limited, waiting {wait}s …")
                time.sleep(wait)
                continue
            print(f"    ⚠ HTTP {r.status_code}: {r.text[:200]}")
            return None
        except httpx.HTTPError as e:
            print(f"    ⚠ HTTP error on attempt {attempt+1}: {e}")
            time.sleep(2)
    return None


def extract_author(staff: dict) -> str | None:
    """Extract author from AniList staff edges."""
    if not staff or "edges" not in staff or not staff["edges"]:
        return None
        
    edges = staff["edges"]
    
    # Try to find someone with "Story" in their role
    for edge in edges:
        roles = str(edge.get("role", "")).lower()
        if "story" in roles:
            return edge.get("node", {}).get("name", {}).get("full")
            
    # Fallback to the first staff member listed
    first_edge = edges[0]
    return first_edge.get("node", {}).get("name", {}).get("full")


def parse_external_link_token(link: dict) -> str | None:
    """Map AniList external link URLs/sites to normalized cross-source tokens."""
    if not isinstance(link, dict):
        return None

    url = (link.get("url") or "").strip()
    site = (link.get("site") or "").strip().lower()
    url_l = url.lower()

    if "myanimelist" in url_l or "myanimelist" in site:
        match = re.search(r"/manga/(\d+)", url_l)
        if match:
            return f"mal:{match.group(1)}"

    if "mangadex" in url_l or "mangadex" in site:
        match = re.search(r"/title/([0-9a-f-]{8,})", url_l)
        if match:
            return f"mangadex:{match.group(1)}"

    if "kitsu" in url_l or "kitsu" in site:
        match = re.search(r"/manga/([0-9a-z-]+)", url_l)
        if match:
            return f"kitsu:{match.group(1)}"

    if "anilist" in url_l or "anilist" in site:
        match = re.search(r"/manga/(\d+)", url_l)
        if match:
            return f"anilist:{match.group(1)}"

    return None


def extract_cross_link_ids(media: dict, mal_id: str | int | None) -> list[str]:
    """Build a stable list of source-prefixed link IDs from AniList externalLinks."""
    tokens = set()

    for link in media.get("externalLinks") or []:
        token = parse_external_link_token(link)
        if token:
            tokens.add(token)

    if mal_id:
        tokens.add(f"mal:{str(mal_id).strip()}")

    return sorted(tokens)


def load_resume_state() -> dict | None:
    """Load persisted resume cursor if present and valid."""
    if not os.path.exists(RESUME_STATE_PATH):
        return None

    try:
        with open(RESUME_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        country = data.get("country")
        page = int(data.get("page", 1))
        if country in COUNTRIES and page >= 1:
            return {"country": country, "page": page}
    except Exception as e:
        print(f"    ⚠ Could not read resume state: {e}")
    return None


def save_resume_state(country: str, page: int):
    """Persist resume cursor so interrupted runs can continue safely."""
    payload = {
        "country": country,
        "page": max(1, int(page)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(RESUME_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def clear_resume_state():
    """Remove persisted resume cursor after a full successful run."""
    if os.path.exists(RESUME_STATE_PATH):
        os.remove(RESUME_STATE_PATH)


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

def fetch_and_stream(test_mode: bool = False):
    """
    Paginate through AniList for each country (KR, CN), process page
    by page, upsert immediately, and write to JSON incrementally.
    """
    total_processed = 0
    interrupted = False
    
    json_path = os.path.join(os.path.dirname(__file__), "anilist_raw.json")
    
    print("=" * 60)

    # Prefer auto-resume from last checkpoint; fallback to constants.
    persisted_resume = load_resume_state()
    if persisted_resume:
        print(
            f"  Resume checkpoint found → country={persisted_resume['country']} "
            f"page={persisted_resume['page']}"
        )
    else:
        print(f"  Resume fallback → country={RESUME_COUNTRY} page={RESUME_PAGE}")
    print("  AniList Fetcher — Korean & Chinese Manga")
    if test_mode:
        print("  [TEST MODE] Will stop after 1 page per country.")
    print("=" * 60)

    # Open JSON file as a stream
    try:
        f = open(json_path, "w", encoding="utf-8")
        f.write("[\n")
        first_record_written = False
        
        resume_country = persisted_resume["country"] if persisted_resume else RESUME_COUNTRY
        resume_page = persisted_resume["page"] if persisted_resume else RESUME_PAGE
        resume_idx = COUNTRIES.index(resume_country)

        for country_idx, country in enumerate(COUNTRIES):
            if country_idx < resume_idx:
                continue

            label = "Korean (manhwa)" if country == "KR" else "Chinese (manhua)"
            print(f"\n{'─'*60}")
            print(f"  Fetching {label} — country={country}")
            print(f"{'─'*60}")
            
            page_num = resume_page if country == resume_country else 1
            has_next = True
            
            while has_next:
                print(f"\n  [{country}] Fetching page {page_num} …")
                
                payload = {
                    "query": GRAPHQL_QUERY,
                    "variables": {"page": page_num, "country": country}
                }
                
                data = safe_post(ANILIST_URL, payload)
                
                if not data or "data" not in data or not data["data"]:
                    print("  No data returned — stopping this country.")
                    break
                    
                page_data = data["data"].get("Page", {})
                page_info = page_data.get("pageInfo", {})
                media_list = page_data.get("media", [])
                
                if not media_list:
                    print("  Empty page — done with this country.")
                    break
                    
                has_next = page_info.get("hasNextPage", False)
                page_records: list[dict] = []
                
                for media in media_list:
                    # ── Title ──
                    title = "Unknown Title"
                    if media.get("title"):
                        title = media["title"].get("english") or media["title"].get("romaji", "Unknown Title")
                        
                    # ── Status ──
                    raw_status = media.get("status")
                    status = "completed" if raw_status == "FINISHED" else "ongoing"
                    
                    # ── Genres ──
                    genres = media.get("genres", [])
                    
                    # ── Summary/Description ──
                    summary = media.get("description")
                    
                    # ── Ratings / Popularity ──
                    raw_rating = media.get("averageScore")
                    if raw_rating is None:
                        raw_rating = media.get("meanScore")
                    try:
                        rating = float(raw_rating) if raw_rating is not None else None
                    except (TypeError, ValueError):
                        rating = None
                    popularity = media.get("popularity", 0)

                    # ── Cross-source IDs / Alt titles ──
                    anilist_id = media.get("id")
                    mal_id = media.get("idMal")
                    synonyms = media.get("synonyms") or []
                    if not mal_id:
                        for link in media.get("externalLinks") or []:
                            url = (link or {}).get("url") or ""
                            site = ((link or {}).get("site") or "").lower()
                            if "myanimelist" in url.lower() or "myanimelist" in site:
                                m = re.search(r"/manga/(\d+)", url)
                                if m:
                                    mal_id = m.group(1)
                                    break

                    cross_link_ids = extract_cross_link_ids(media, mal_id)

                    cleaned_synonyms = []
                    seen_synonyms = set()
                    for s in synonyms:
                        if not isinstance(s, str):
                            continue
                        s_norm = s.strip()
                        if not s_norm:
                            continue
                        key = s_norm.lower()
                        if key in seen_synonyms:
                            continue
                        seen_synonyms.add(key)
                        cleaned_synonyms.append(s_norm)
                    
                    # ── Chapter count (keep None for ongoing/unknown) ──
                    chapter_count = media.get("chapters")
                    
                    # ── Cover image ──
                    cover_image = None
                    if media.get("coverImage"):
                        cover_image = media["coverImage"].get("large")
                    
                    # ── Author ──
                    author = extract_author(media.get("staff", {}))
                    
                    # ── Status Distribution ──
                    status_dist = {}
                    for entry in media.get("stats", {}).get("statusDistribution", []):
                        status_dist[entry["status"]] = entry["amount"]

                    record = {
                        "title": title,
                        "author": author,
                        "genres": genres,
                        "chapter_count": chapter_count,
                        "rating": rating,
                        "rating_count": popularity,
                        "view_count": popularity,
                        "status": status,
                        "summary": summary,
                        "source_site": "anilist",
                        "cover_image": cover_image,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "count_current": status_dist.get("CURRENT", 0),
                        "count_completed": status_dist.get("COMPLETED", 0),
                        "count_dropped": status_dist.get("DROPPED", 0),
                        "count_paused": status_dist.get("PAUSED", 0),
                        "count_planning": status_dist.get("PLANNING", 0),
                        "external_id": str(anilist_id) if anilist_id else None,
                        "mal_cross_id": str(mal_id) if mal_id else None,
                        "alt_titles": cleaned_synonyms,
                        "cross_link_ids": cross_link_ids,
                    }
                    
                    page_records.append(record)
                    
                    # Stream to JSON file incrementally
                    if first_record_written:
                        f.write(",\n")
                    json.dump(record, f, ensure_ascii=False, indent=2)
                    first_record_written = True

                # ── Upsert page to Supabase ──
                upserted = upsert_to_supabase(page_records)
                
                total_processed += len(page_records)
                print(f"  ✓ [{country}] Page {page_num} | Upserted: {upserted} | Total: {total_processed} | Has next: {has_next}")

                # Persist progress after each successful page.
                if has_next:
                    save_resume_state(country, page_num + 1)
                elif country_idx + 1 < len(COUNTRIES):
                    save_resume_state(COUNTRIES[country_idx + 1], 1)
                else:
                    clear_resume_state()
                
                # ── Free memory immediately ──
                page_records = []
                
                if test_mode:
                    print(f"  Test mode limit reached for {country}.")
                    break
                    
                page_num += 1

    except KeyboardInterrupt:
        interrupted = True
        print("\n\n  ⚠ Interrupted by user (Ctrl+C).")
        # Save cursor at current page so rerun continues from this point.
        if 'country' in locals() and 'page_num' in locals():
            save_resume_state(country, page_num)
            print(f"  Resume saved → country={country} page={page_num}")
        else:
            print("  Resume state unchanged.")

    finally:
        # Close the JSON array gracefully
        if 'f' in locals() and not f.closed:
            f.write("\n]\n")
            f.close()
            print(f"\n  💾 Closed JSON file at {json_path}")

        if interrupted:
            print(f"  💡 Rerun the same command to continue from {RESUME_STATE_PATH}")
            
    return total_processed


# ────────────────────────────────────────────────────────────
#  Entry point
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    start = time.time()
    
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"
    
    total = fetch_and_stream(test_mode=test_mode)
    
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  DONE — {total} total manga | {elapsed:.0f}s elapsed")
    print(f"{'='*60}")
    
    client.close()
