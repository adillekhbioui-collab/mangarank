import os
import sys
import json
import httpx
import csv
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

def fetch_all() -> list[dict]:
    headers = supabase_headers()
    all_records = []
    offset = 0
    page_size = 1000

    print("Fetching records from manga...", file=sys.stderr)

    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/manga_raw"
            f"?select=genres"
            f"&order=id.asc"
            f"&offset={offset}"
            f"&limit={page_size}"
        )
        r = httpx.get(url, headers=headers, timeout=30)
        
        if r.status_code not in (200, 206):
            print(f"Fetch failed at offset {offset}: {r.status_code}", file=sys.stderr)
            break

        rows = r.json()
        if not rows:
            break

        all_records.extend(rows)

        if len(rows) < page_size:
            break

        offset += page_size

    return all_records

if __name__ == "__main__":
    records = fetch_all()
    unique_genres = set()

    for rec in records:
        genres = rec.get("genres")
        if not genres:
            continue
        if isinstance(genres, str):
            try:
                genres = json.loads(genres)
            except:
                genres = [genres]

        if isinstance(genres, list):
            for gen in genres:
                g = str(gen).strip().title()
                if g:
                    unique_genres.add(g)

    csv_file = "genres_blacklist.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Genre", "Blacklisted"])
        for g in sorted(unique_genres):
            writer.writerow([g, "no"])

    print(f"Successfully wrote {len(unique_genres)} unique genres to {csv_file}")
