"""
Step 2 — Create Supabase tables: manga_raw and manga_rankings.

Uses the Supabase REST API to execute SQL via the pg_net extension
or direct PostgREST. Since the anon key may not have DDL permissions,
this script outputs the SQL so you can paste it into the Supabase
SQL Editor, and also attempts to create the tables via the API.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ── SQL statements ──────────────────────────────────────────

CREATE_MANGA_RAW = """
CREATE TABLE IF NOT EXISTS manga_raw (
    id            SERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    author        TEXT,
    genres        TEXT[],
    chapter_count INTEGER,
    rating        FLOAT,
    rating_count  INTEGER,
    view_count    INTEGER,
    status        TEXT,
    source_site   TEXT NOT NULL,
    cover_image   TEXT,
    fetched_at    TIMESTAMP DEFAULT now(),
    UNIQUE (title, source_site)
);
"""

CREATE_MANGA_RANKINGS = """
CREATE TABLE IF NOT EXISTS manga_rankings (
    id                SERIAL PRIMARY KEY,
    title             TEXT UNIQUE NOT NULL,
    author            TEXT,
    genres            TEXT[],
    chapter_count     INTEGER,
    aggregated_score  FLOAT,
    total_views       BIGINT,
    status            TEXT,
    cover_image       TEXT,
    updated_at        TIMESTAMP DEFAULT now()
);
"""

def create_tables_via_rest():
    """
    Attempt to create tables using Supabase's REST SQL endpoint.
    This requires the service_role key or a database function.
    """
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    # Try using the rpc endpoint with a raw SQL function
    # First, let's try the direct SQL execution via PostgREST's rpc
    sql_statements = [
        ("manga_raw", CREATE_MANGA_RAW),
        ("manga_rankings", CREATE_MANGA_RANKINGS),
    ]

    for table_name, sql in sql_statements:
        print(f"\n{'='*50}")
        print(f"Creating table: {table_name}")
        print(f"{'='*50}")

        # Try via Supabase's SQL endpoint
        response = httpx.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": sql},
            timeout=30
        )

        if response.status_code in (200, 201, 204):
            print(f"✓ Table '{table_name}' created successfully via RPC!")
        else:
            print(f"  RPC method returned {response.status_code}: {response.text}")
            print(f"  This is expected if the exec_sql function doesn't exist yet.")

    return False


def print_manual_sql():
    """Print SQL for manual execution in Supabase SQL Editor."""
    print("\n" + "=" * 60)
    print("  MANUAL SETUP — Copy this SQL into your Supabase SQL Editor")
    print("  (Dashboard → SQL Editor → New query → Paste → Run)")
    print("=" * 60)

    full_sql = f"""
-- ============================================
-- Manhwa Aggregator — Database Setup
-- ============================================

-- Table 1: manga_raw (one row per manga per source)
{CREATE_MANGA_RAW}

-- Table 2: manga_rankings (one row per unique manga, production table)
{CREATE_MANGA_RANKINGS}

-- Enable Row Level Security (allow all reads for anon key)
ALTER TABLE manga_raw ENABLE ROW LEVEL SECURITY;
ALTER TABLE manga_rankings ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read on manga_raw"
    ON manga_raw FOR SELECT
    USING (true);

CREATE POLICY "Allow public read on manga_rankings"
    ON manga_rankings FOR SELECT
    USING (true);

-- Allow authenticated insert/update/delete
CREATE POLICY "Allow service role full access on manga_raw"
    ON manga_raw FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow service role full access on manga_rankings"
    ON manga_rankings FOR ALL
    USING (true)
    WITH CHECK (true);

-- Confirm
SELECT 'Tables created successfully!' AS status;
"""
    print(full_sql)
    return full_sql


def verify_tables():
    """Check if the tables exist by attempting a read via PostgREST."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

    print("\n" + "=" * 50)
    print("  VERIFICATION — Checking if tables exist")
    print("=" * 50)

    for table in ["manga_raw", "manga_rankings"]:
        response = httpx.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=0",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            print(f"  ✓ Table '{table}' exists and is accessible!")
        else:
            print(f"  ✗ Table '{table}' not found (status {response.status_code})")
            print(f"    → Please create it via the SQL Editor (see SQL above)")


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        exit(1)

    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Key type: {'service_role' if 'service_role' in SUPABASE_KEY else 'anon/publishable'}")

    # Try automated creation first
    create_tables_via_rest()

    # Print SQL for manual creation
    sql = print_manual_sql()

    # Verify tables
    verify_tables()

    print("\n" + "=" * 50)
    print("  NEXT STEPS")
    print("=" * 50)
    print("  If tables show ✗ above, paste the SQL into your")
    print("  Supabase SQL Editor and run it, then re-run this script.")
    print("=" * 50)
