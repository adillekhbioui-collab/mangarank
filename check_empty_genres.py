import os
import httpx
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
}

def count_records(table: str, filter_query: str) -> int:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filter_query}&select=id"
    count = 0
    offset = 0
    page_size = 1000
    while True:
        r = httpx.get(f"{url}&offset={offset}&limit={page_size}", headers=headers, timeout=30)
        if r.status_code not in (200, 206):
            break
        data = r.json()
        if not data:
            break
        count += len(data)
        if len(data) < page_size:
            break
        offset += page_size
    return count

print("Counting in manga_rankings...")
try:
    null_count = count_records("manga_rankings", "genres=is.null")
    empty_count = count_records("manga_rankings", "genres=eq.{}")
except Exception as e:
    print(f"Error: {e}")
print(f"manga_rankings -> null genres: {null_count}, empty array genres: {empty_count}")

print("Counting in manga_raw...")
try:
    raw_null_count = count_records("manga_raw", "genres=is.null")
    raw_empty_count = count_records("manga_raw", "genres=eq.{}")
except Exception as e:
    print(f"Error: {e}")
print(f"manga_raw -> null genres: {raw_null_count}, empty array genres: {raw_empty_count}")
