import os
import sys
import json
import csv
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

def get_nsfw_categories(csv_path: str) -> set:
    nsfw_cats = set()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Is NSFW", "").strip().lower() == "yes":
                    nsfw_cats.add(row["Category"].strip().title())
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        sys.exit(1)
    return nsfw_cats

def fetch_all_manga() -> list[dict]:
    headers = supabase_headers()
    all_records = []
    offset = 0
    page_size = 1000

    print("Fetching all manga records...")
    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/manga_raw"
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

def delete_manga_batch(ids_to_delete: list):
    """
    Deletes manga records in batches of chunk_size to avoid URI length limits.
    Note: Supabase will cascade delete related manga_rankings if set up, 
    otherwise we might encounter foreign key constraint errors.
    """
    headers = supabase_headers()
    chunk_size = 100
    total_deleted = 0
    
    with open("nsfw_deletion_log.txt", "w", encoding="utf-8") as log:
        for i in range(0, len(ids_to_delete), chunk_size):
            chunk = ids_to_delete[i:i + chunk_size]
            # Create a comma-separated list of IDs
            id_list = ",".join(str(cid) for cid in chunk)
            url = f"{SUPABASE_URL}/rest/v1/manga_raw?id=in.({id_list})"
            
            # Using DELETE request
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
    csv_file = os.path.join(os.path.dirname(__file__), "categories_report.csv")
    nsfw_categories = get_nsfw_categories(csv_file)
    
    print(f"Loaded {len(nsfw_categories)} NSFW categories exactly from CSV.")
    print(f"Categories flagged for deletion: {', '.join(nsfw_categories)}")
    print("-" * 40)
    
    records = fetch_all_manga()
    print(f"Total manga fetched: {len(records)}")
    
    ids_to_delete = []
    
    for rec in records:
        rec_id = rec.get("id")
        genres = rec.get("genres")
        
        if not genres:
            continue
            
        # Parse genres similar to previously
        if isinstance(genres, str):
            try:
                genres = json.loads(genres)
            except:
                genres = [genres]
                
        if isinstance(genres, list):
            # Check if any parsed genre intersects with our NSFW categories set
            has_nsfw = any(str(g).strip().title() in nsfw_categories for g in genres if g)
            if has_nsfw:
                ids_to_delete.append(rec_id)
                
    print(f"Identified {len(ids_to_delete)} manga containing NSFW categories.")
    
    if ids_to_delete:
        print("Starting deletion process...")
        deleted_count = delete_manga_batch(ids_to_delete)
        print("-" * 40)
        print(f"Process complete. Successfully deleted {deleted_count} matching manga.")
        print("Check 'nsfw_deletion_log.txt' for the exact IDs deleted.")
    else:
        print("No NSFW manga found to delete.")
