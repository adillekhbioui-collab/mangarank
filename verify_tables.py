import os
import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
headers = {"apikey": key, "Authorization": f"Bearer {key}"}

print("Verifying Supabase tables...")
for table in ["manga_raw", "manga_rankings"]:
    try:
        r = httpx.get(f"{url}/rest/v1/{table}?select=*&limit=0", headers=headers, timeout=15)
        if r.status_code == 200:
            print(f"  OK  - {table} exists and is accessible")
        else:
            print(f"  FAIL - {table} returned status {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  ERROR - {table}: {e}")

print("\nDone!")
