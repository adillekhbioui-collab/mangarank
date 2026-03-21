import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ALTER_TABLES_SQL = """
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE manga_rankings ADD COLUMN IF NOT EXISTS summary TEXT;
"""

def add_summary_column():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    print("Attempting to add 'summary' column to manga_raw and manga_rankings...")
    
    response = httpx.post(
        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
        headers=headers,
        json={"query": ALTER_TABLES_SQL},
        timeout=30
    )

    if response.status_code in (200, 201, 204):
        print("✓ Tables altered successfully via RPC!")
    else:
        print(f"RPC method returned {response.status_code}: {response.text}")
        print("Please run the following SQL manually in the Supabase SQL Editor:")
        print("-" * 50)
        print(ALTER_TABLES_SQL)
        print("-" * 50)

if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        exit(1)
    
    add_summary_column()
