import os
import sys
import time
import json
import argparse
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID")

if not SUPABASE_URL or not SUPABASE_KEY or not MAL_CLIENT_ID:
    print("Error: Missing SUPABASE_URL, SUPABASE_KEY, or MAL_CLIENT_ID in .env")
    sys.exit(1)

DELAY = 1.0
BASE_URL = "https://api.myanimelist.net/v2"

# Resume configuration
RESUME_SUBTYPE = "manhwa"  # Change to "manhua" if manhwa finished
RESUME_OFFSET = 0

client = httpx.Client(
    headers={"X-MAL-CLIENT-ID": MAL_CLIENT_ID},
    timeout=httpx.Timeout(30.0),
    follow_redirects=True,
)

supabase_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal"
}

def safe_get(url, params=None, retries=3):
    for attempt in range(retries):
        time.sleep(DELAY)
        try:
            response = client.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                print(f"Rate limited (429). Waiting {retry_after}s...")
                time.sleep(retry_after)
            elif response.status_code == 403:
                print("Check your MAL_CLIENT_ID (403 Forbidden)")
                return None
            elif response.status_code == 404:
                return None
            elif response.status_code in (500, 503):
                print(f"Server error {response.status_code}. Waiting 10s...")
                time.sleep(10)
            else:
                print(f"Unexpected status code {response.status_code} for {url}. Retrying...")
                time.sleep(5)
                
        except httpx.RequestError as e:
            print(f"Request error: {e}. Retrying...")
            time.sleep(5)
            
    print(f"Failed to fetch {url} after {retries} retries.")
    return None

def extract_manga_data(node, target_subtype):
    media_type = node.get("media_type")
    if media_type != target_subtype:
        return None
        
    nsfw = node.get("nsfw")
    if nsfw != "white":
        return None
        
    # IDs
    mal_id = node.get("id")

    # Title
    title = node.get("title", "")
    alt_titles = node.get("alternative_titles", {})
    en_title = alt_titles.get("en", "")
    final_title = en_title if en_title else title
    
    if not final_title:
        return None

    # Alternative titles
    synonyms = alt_titles.get("synonyms", [])
    if not isinstance(synonyms, list):
        synonyms = []
    alt_title_list = []
    if en_title:
        alt_title_list.append(en_title)
    alt_title_list.extend([s for s in synonyms if isinstance(s, str)])
    dedup_alt_titles = []
    seen = set()
    for s in alt_title_list:
        clean_s = s.strip()
        if not clean_s:
            continue
        key = clean_s.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup_alt_titles.append(clean_s)
        
    # Author
    author_name = None
    authors = node.get("authors", [])
    if authors:
        story_author = next((a for a in authors if a.get("role") == "Story"), None)
        target_author = story_author if story_author else authors[0]
        node_author = target_author.get("node", {})
        first = node_author.get("first_name", "")
        last = node_author.get("last_name", "")
        author_name = f"{first} {last}".strip() if first or last else None
        
    # Genres
    genres = [g.get("name") for g in node.get("genres", []) if g.get("name")]
    
    # Chapter Count
    chapter_count = node.get("num_chapters") or 0
    
    # Rating
    mean = node.get("mean")
    rating = float(mean) * 10 if mean is not None else None
    
    # Rating Count
    rating_count = node.get("num_scoring_users") or 0
    
    # View Count
    view_count = node.get("num_list_users") or 0
    
    # Status
    mal_status = node.get("status", "")
    status_map = {
        "finished": "completed",
        "currently_publishing": "ongoing",
        "not_yet_published": "ongoing",
        "discontinued": "completed",
        "on_hiatus": "ongoing"
    }
    status = status_map.get(mal_status, mal_status)
    
    # Cover Image
    main_picture = node.get("main_picture", {})
    cover_image = main_picture.get("large") or main_picture.get("medium") or None
    
    return {
        "title": final_title,
        "author": author_name,
        "genres": genres,
        "chapter_count": chapter_count,
        "rating": rating,
        "rating_count": rating_count,
        "view_count": view_count,
        "status": status,
        "cover_image": cover_image,
        "source_site": "mal",
        "external_id": str(mal_id) if mal_id else None,
        "alt_titles": dedup_alt_titles,
    }

def upsert_to_supabase(records):
    if not records:
        return True
        
    url = f"{SUPABASE_URL}/rest/v1/manga_raw?on_conflict=title,source_site"
    try:
        response = httpx.post(url, headers=supabase_headers, json=records, timeout=30.0)
        response.raise_for_status()
        return True
    except httpx.HTTPError as e:
        print(f"Supabase upsert failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run in test mode (max 200 records)")
    args = parser.parse_args()
    
    subtypes = ["manhwa", "manhua"]
    
    if RESUME_SUBTYPE in subtypes:
        start_idx = subtypes.index(RESUME_SUBTYPE)
        subtypes = subtypes[start_idx:]
        
    fields = "title,alternative_titles,mean,num_scoring_users,num_list_users,media_type,status,genres,num_chapters,authors{node{first_name,last_name}},main_picture,rank,popularity,nsfw"
    
    total_upserted = {"manhwa": 0, "manhua": 0}
    test_limit = 200
    grand_total_kept = 0
    start_time = time.time()
    
    out_file = open(os.path.join(os.path.dirname(__file__), "mal_raw.json"), "w", encoding="utf-8")
    out_file.write("[\n")
    first_record_written = False
    
    try:
        for subtype in subtypes:
            offset = RESUME_OFFSET if subtype == RESUME_SUBTYPE else 0
            empty_pages = 0
            subtype_kept = 0
            
            print(f"\nStarting {subtype.upper()} fetch...")
            
            while offset < 50000:
                # Query subtype ranking directly; this yields much better coverage
                # than pulling "all" rankings and filtering locally.
                params = {
                    "ranking_type": subtype,
                    "limit": 100,
                    "offset": offset,
                    "fields": fields
                }
                
                data = safe_get(f"{BASE_URL}/manga/ranking", params=params)
                if not data:
                    break
                    
                nodes = [item.get("node", {}) for item in data.get("data", [])]
                if not nodes:
                    break
                    
                page_records = []
                fetched = len(nodes)
                
                for node in nodes:
                    record = extract_manga_data(node, target_subtype=subtype)
                    if record:
                        page_records.append(record)
                        
                        # Write to JSON
                        if first_record_written:
                            out_file.write(",\n")
                        json.dump(record, out_file, ensure_ascii=False)
                        first_record_written = True
                
                kept = len(page_records)
                success = True
                upserted_count = 0
                if kept == 0:
                    empty_pages += 1
                else:
                    empty_pages = 0
                    success = upsert_to_supabase(page_records)
                    upserted_count = kept if success else 0
                    if success:
                        subtype_kept += kept
                        grand_total_kept += kept
                        total_upserted[subtype] += kept

                print(f"[{subtype}] offset={offset} | fetched: {fetched} | kept: {kept} | upserted: {upserted_count} | subtype total: {subtype_kept} | grand total: {grand_total_kept}")
                
                if args.test and grand_total_kept >= test_limit:
                    print(f"\nTest limit reached ({test_limit} records). Stopping.")
                    return
                    
                if empty_pages >= 50:
                    print(f"50 consecutive empty pages for {subtype}. Moving to next.")
                    break
                    
                paging_next = data.get("paging", {}).get("next")
                if not paging_next:
                    break
                    
                offset += 100
                
            print(f"{subtype.upper()} complete — total upserted: {total_upserted[subtype]}")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        out_file.write("\n]")
        out_file.close()
        client.close()
        
        elapsed = (time.time() - start_time) / 60
        print("\nDONE")
        print(f"manhwa : {total_upserted.get('manhwa', 0)}")
        print(f"manhua : {total_upserted.get('manhua', 0)}")
        total = sum(total_upserted.values())
        print(f"total  : {total}")
        print(f"elapsed: {elapsed:.1f} minutes")

if __name__ == "__main__":
    main()