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

def fetch_all_raw() -> list[dict]:
    headers = supabase_headers()
    headers["Prefer"] = "count=exact"
    all_records = []
    offset = 0
    page_size = 1000

    print("Fetching records from manga_raw...", file=sys.stderr)

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

NSFW_KEYWORDS = {"adult", "mature", "smut", "hentai", "ecchi", "doujinshi", "pornographic", "erotica", "borderline h", "yaoi", "yuri"}

if __name__ == "__main__":
    records = fetch_all_raw()
    
    category_counts = {}
    
    for rec in records:
        genres = rec.get("genres")
        if not genres:
            continue
        if isinstance(genres, str):
            try:
                # in case they are stored as JSON strings
                genres = json.loads(genres)
            except:
                genres = [genres]
        
        if isinstance(genres, list):
            for gen in genres:
                g = str(gen).strip().title()
                if not g:
                    continue
                category_counts[g] = category_counts.get(g, 0) + 1
    
    # Sort categories by count descending
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    csv_file = "categories_report.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Manga Count", "Is NSFW"])
        
        for cat, count in sorted_categories:
            cat_lower = cat.lower()
            is_nsfw = "Yes" if any(k in cat_lower for k in NSFW_KEYWORDS) else "No"
            writer.writerow([cat, count, is_nsfw])
    
    print(f"Successfully wrote {len(sorted_categories)} categories to {csv_file}")
