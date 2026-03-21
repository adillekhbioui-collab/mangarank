import os
import sys
import json
import csv
import httpx
from dotenv import load_dotenv

# Load env variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
load_dotenv(env_path)

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

def get_blacklisted_genres(csv_path: str) -> set:
    blacklisted = set()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Blacklisted", "").strip().lower() == "yes":
                    blacklisted.add(row["Genre"].strip().title())
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        sys.exit(1)
    return blacklisted

def fetch_all_manga(table="manga_raw") -> list[dict]:
    headers = supabase_headers()
    all_records = []
    offset = 0
    page_size = 1000

    print(f"Fetching all manga records from {table}...")
    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/{table}"
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

def delete_manga_batch(table: str, ids_to_delete: list):
    headers = supabase_headers()
    chunk_size = 100
    total_deleted = 0

    log_filename = f"blacklist_deletion_log_{table}.txt"
    with open(log_filename, "w", encoding="utf-8") as log:
        for i in range(0, len(ids_to_delete), chunk_size):
            chunk = ids_to_delete[i:i + chunk_size]
            id_list = ",".join(str(cid) for cid in chunk)
            url = f"{SUPABASE_URL}/rest/v1/{table}?id=in.({id_list})"

            r = httpx.delete(url, headers=headers, timeout=30)

            if r.status_code in (200, 204):
                total_deleted += len(chunk)
                print(f"Successfully deleted batch {i // chunk_size + 1} ({len(chunk)} records) from {table}")
                for cid in chunk:
                    log.write(f"Deleted ID: {cid}\n")
            else:
                print(f"Failed to delete batch {i // chunk_size + 1} from {table}: {r.status_code} - {r.text}")
                
    return total_deleted

def process_table(table: str, blacklisted_genres: set):
    print(f"--- Processing table: {table} ---")
    records = fetch_all_manga(table)
    print(f"Total manga fetched: {len(records)}")

    ids_to_delete = []

    for rec in records:
        rec_id = rec.get("id")
        genres = rec.get("genres")

        if not genres:
            continue

        if isinstance(genres, str):
            try:
                # the genres string might be single quoted or malformed JSON
                genres_clean = genres.replace("'", '"')
                genres = json.loads(genres_clean)
            except:
                genres = [genres]

        if isinstance(genres, list):
            has_blacklisted = any(str(g).strip().title() in blacklisted_genres for g in genres if g)
            if has_blacklisted:
                ids_to_delete.append(rec_id)

    print(f"Identified {len(ids_to_delete)} manga containing blacklisted genres in {table}.")

    if ids_to_delete:
        print(f"Starting deletion process for {table}...")
        deleted_count = delete_manga_batch(table, ids_to_delete)
        print(f"Process complete for {table}. Successfully deleted {deleted_count} matching manga.")
    else:
        print(f"No manga needed deletion in {table}.")

if __name__ == "__main__":
    csv_file = os.path.join(os.path.dirname(__file__), "genres_blacklist.csv")
    blacklisted_genres = get_blacklisted_genres(csv_file)

    if not blacklisted_genres:
        print("No blacklisted genres found. Exiting.")
        sys.exit(0)

    print(f"Loaded {len(blacklisted_genres)} blacklisted genres exactly from CSV.")
    print(f"Genres flagged for deletion: {', '.join(blacklisted_genres)}\n")

    # The DB typically has manga and manga_raw, or just manga. 
    # We will process both just in case, but you can comment out the one you don't need.
    process_table("manga_raw", blacklisted_genres)
    process_table("manga", blacklisted_genres)
