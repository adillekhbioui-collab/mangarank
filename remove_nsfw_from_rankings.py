import os
import sys
import json
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

# The 19 NSFW categories selected by the user
NSFW_CATEGORIES = {
    "Monster Girls",
    "Hentai",
    "Yaoi",
    "Mahou Shoujo",
    "Loli",
    "4-Koma",
    "Genderswap",
    "Shota",
    "Boys' Love",
    "Oneshot",
    "Girls' Love",
    "Sexual Violence",
    "Doujinshi",
    "Mature",
    "Gender Bender",
    "Incest",
    "Reverse Harem",
    "Ecchi",
    "Yuri"
}

def fetch_all_manga_rankings() -> list[dict]:
    headers = supabase_headers()
    all_records = []
    offset = 0
    page_size = 1000

    print("Fetching all manga records from manga_rankings...")
    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/manga_rankings"
            f"?select=id,title,genres"
            f"&order=id.asc"
            f"&offset={offset}"
            f"&limit={page_size}"
        )
        r = httpx.get(url, headers=headers, timeout=30)
        
        if r.status_code not in (200, 206):
            print(f"Fetch failed at offset {offset}: {r.status_code}")
            break
            
        rows = r.json()
        if not rows:
            break
            
        all_records.extend(rows)
        if len(rows) < page_size:
            break
            
        offset += page_size
        
    return all_records

def delete_manga_rankings_batch(ids_to_delete: list):
    headers = supabase_headers()
    chunk_size = 100
    total_deleted = 0
    
    with open("nsfw_deletion_rankings_log.txt", "w", encoding="utf-8") as log:
        for i in range(0, len(ids_to_delete), chunk_size):
            chunk = ids_to_delete[i:i + chunk_size]
            id_list = ",".join(f'"{cid}"' if isinstance(cid, str) else str(cid) for cid in chunk)
            url = f"{SUPABASE_URL}/rest/v1/manga_rankings?id=in.({id_list})"
            
            r = httpx.delete(url, headers=headers, timeout=30)
            
            if r.status_code in (200, 204):
                total_deleted += len(chunk)
                print(f"Successfully deleted batch {i // chunk_size + 1} ({len(chunk)} records)")
                for cid in chunk:
                    log.write(f"Deleted ID: {cid}\n")
            else:
                print(f"Failed to delete batch {i // chunk_size + 1}: {r.status_code} - {r.text}")
                
    return total_deleted

if __name__ == "__main__":
    print(f"Loaded {len(NSFW_CATEGORIES)} NSFW categories manually.")
    print("-" * 40)
    
    records = fetch_all_manga_rankings()
    print(f"Total manga fetched: {len(records)}")
    
    ids_to_delete = []
    
    for rec in records:
        rec_id = rec.get("id")
        genres = rec.get("genres")
        
        if not genres:
            continue
            
        # Parse genres
        if isinstance(genres, str):
            try:
                genres = json.loads(genres)
            except:
                genres = [genres]
                
        if isinstance(genres, list):
            has_nsfw = any(str(g).strip().title() in NSFW_CATEGORIES for g in genres if g)
            if has_nsfw:
                ids_to_delete.append(rec_id)
                
    print(f"Identified {len(ids_to_delete)} manga containing NSFW categories in manga_rankings.")
    
    if ids_to_delete:
        print("Starting deletion process for manga_rankings...")
        deleted_count = delete_manga_rankings_batch(ids_to_delete)
        print("-" * 40)
        print(f"Process complete. Successfully deleted {deleted_count} matching manga from manga_rankings.")
    else:
        print("No NSFW manga found to delete in manga_rankings.")
