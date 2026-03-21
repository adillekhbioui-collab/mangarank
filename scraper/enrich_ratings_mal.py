"""
Targeted MAL rating enrichment.

Updates only rows in manga_raw where:
- source_site = 'mal'
- rating IS NULL
- external_id IS NOT NULL

Calls MAL per-id endpoint for minimal fields only and PATCHes rating columns.
"""

import json
import os
import sys
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID")
MAL_BASE_URL = "https://api.myanimelist.net/v2"

REQUEST_DELAY = 1.0
BATCH_FETCH = 200
STATE_PATH = os.path.join(os.path.dirname(__file__), "enrich_ratings_mal.state.json")

if not SUPABASE_URL or not SUPABASE_KEY or not MAL_CLIENT_ID:
    print("Error: SUPABASE_URL / SUPABASE_KEY / MAL_CLIENT_ID missing in .env")
    sys.exit(1)

sb_client = httpx.Client(timeout=30, follow_redirects=True)
mal_client = httpx.Client(
    timeout=30,
    follow_redirects=True,
    headers={"X-MAL-CLIENT-ID": MAL_CLIENT_ID},
)


def sb_headers(prefer: str = "return=minimal") -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {"last_id": 0}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"last_id": int(data.get("last_id", 0))}
    except Exception:
        return {"last_id": 0}


def save_state(last_id: int):
    payload = {
        "last_id": int(last_id),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def fetch_null_rows(last_id: int, limit: int) -> list[dict]:
    url = (
        f"{SUPABASE_URL}/rest/v1/manga_raw"
        f"?select=id,external_id,view_count"
        f"&source_site=eq.mal"
        f"&rating=is.null"
        f"&external_id=not.is.null"
        f"&id=gt.{last_id}"
        f"&order=id.asc"
        f"&limit={limit}"
    )
    r = sb_client.get(url, headers=sb_headers())
    if r.status_code not in (200, 206):
        raise RuntimeError(f"Supabase fetch failed: {r.status_code} {r.text[:300]}")
    return r.json()


def fetch_mal_rating(mal_id: str) -> dict | None:
    url = f"{MAL_BASE_URL}/manga/{mal_id}"
    params = {
        "fields": "mean,num_scoring_users,num_list_users",
    }

    for attempt in range(3):
        try:
            r = mal_client.get(url, params=params)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", "5"))
                time.sleep(wait)
                continue
            if r.status_code in (500, 502, 503, 504):
                time.sleep(3)
                continue
            print(f"    MAL error {r.status_code} for id={mal_id}: {r.text[:160]}")
            return None
        except httpx.HTTPError:
            if attempt == 2:
                return None
            time.sleep(2)

    return None


def patch_row(row_id: int, payload: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/manga_raw?id=eq.{row_id}"
    for attempt in range(3):
        try:
            r = sb_client.patch(url, headers=sb_headers(), json=payload)
            if r.status_code in (200, 201, 204):
                return True
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", "3"))
                time.sleep(wait)
                continue
            print(f"    PATCH failed for id={row_id}: {r.status_code} {r.text[:160]}")
            return False
        except httpx.HTTPError:
            if attempt == 2:
                return False
            time.sleep(1)
    return False


def main():
    started = time.time()
    state = load_state()
    last_id = state["last_id"]

    processed = 0
    updated = 0
    still_null = 0

    print("=" * 60)
    print("  MAL Targeted Rating Enrichment")
    print("=" * 60)
    print(f"  Resume from id > {last_id}")

    while True:
        rows = fetch_null_rows(last_id=last_id, limit=BATCH_FETCH)
        if not rows:
            break

        for row in rows:
            row_id = int(row["id"])
            mal_id = str(row.get("external_id", "")).strip()

            rec = fetch_mal_rating(mal_id)
            if not rec:
                still_null += 1
                processed += 1
                last_id = row_id
                continue

            mean = rec.get("mean")
            if mean is None:
                still_null += 1
                processed += 1
                last_id = row_id
                if processed % 100 == 0:
                    print(f"  [MAL] {processed} processed | updated: {updated} | null: {still_null}")
                time.sleep(REQUEST_DELAY)
                continue

            try:
                rating = round(float(mean) * 10.0, 2)
            except (TypeError, ValueError):
                still_null += 1
                processed += 1
                last_id = row_id
                time.sleep(REQUEST_DELAY)
                continue

            num_scoring = rec.get("num_scoring_users")
            try:
                rating_count = int(num_scoring) if num_scoring is not None else 0
            except (TypeError, ValueError):
                rating_count = 0

            payload = {
                "rating": rating,
                "rating_count": rating_count,
            }

            # Keep existing view_count unless it is null.
            if row.get("view_count") is None:
                num_list = rec.get("num_list_users")
                try:
                    payload["view_count"] = int(num_list) if num_list is not None else None
                except (TypeError, ValueError):
                    pass

            if patch_row(row_id=row_id, payload=payload):
                updated += 1
            else:
                still_null += 1

            processed += 1
            last_id = row_id
            save_state(last_id)

            if processed % 100 == 0:
                print(f"  [MAL] {processed} processed | updated: {updated} | null: {still_null}")

            time.sleep(REQUEST_DELAY)

        save_state(last_id)

    elapsed = round(time.time() - started, 1)
    print("\nMAL enrichment complete")
    print(f"  Rows processed:      {processed}")
    print(f"  Records updated:    {updated}")
    print(f"  Still null:         {still_null}")
    print(f"  Last processed id:  {last_id}")
    print(f"  Time elapsed:       {elapsed}s")


if __name__ == "__main__":
    main()
