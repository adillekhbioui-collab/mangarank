"""
Targeted MangaDex rating enrichment.

Updates only rows in manga_raw where:
- source_site = 'mangadex'
- rating IS NULL
- external_id IS NOT NULL

For each batch, calls MangaDex statistics endpoint (up to 100 IDs/request)
and PATCHes only rating columns on the matched row IDs.
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
MANGADEX_STATS_URL = "https://api.mangadex.org/statistics/manga"

BATCH_SIZE = 100
REQUEST_DELAY = 0.3
STATE_PATH = os.path.join(os.path.dirname(__file__), "enrich_ratings_mangadex.state.json")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL / SUPABASE_KEY missing in .env")
    sys.exit(1)

client = httpx.Client(timeout=30, follow_redirects=True)


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
        f"&source_site=eq.mangadex"
        f"&rating=is.null"
        f"&external_id=not.is.null"
        f"&id=gt.{last_id}"
        f"&order=id.asc"
        f"&limit={limit}"
    )
    r = client.get(url, headers=sb_headers())
    if r.status_code not in (200, 206):
        raise RuntimeError(f"Supabase fetch failed: {r.status_code} {r.text[:300]}")
    return r.json()


def fetch_md_stats(ids: list[str]) -> dict:
    params = [("manga[]", mid) for mid in ids]
    for attempt in range(3):
        try:
            r = client.get(MANGADEX_STATS_URL, params=params)
            if r.status_code == 200:
                return r.json().get("statistics", {})
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", "5"))
                print(f"  Rate-limited by MangaDex. Waiting {wait}s ...")
                time.sleep(wait)
                continue
            print(f"  MangaDex stats error {r.status_code}: {r.text[:200]}")
            return {}
        except httpx.HTTPError as e:
            if attempt == 2:
                print(f"  MangaDex request failed after retries: {e}")
                return {}
            time.sleep(2)
    return {}


def patch_row(row_id: int, payload: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/manga_raw?id=eq.{row_id}"
    for attempt in range(3):
        try:
            r = client.patch(url, headers=sb_headers(), json=payload)
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

    updated = 0
    still_null = 0
    processed = 0
    batch_no = 0

    print("=" * 60)
    print("  MangaDex Targeted Rating Enrichment")
    print("=" * 60)
    print(f"  Resume from id > {last_id}")

    while True:
        rows = fetch_null_rows(last_id=last_id, limit=BATCH_SIZE)
        if not rows:
            break

        batch_no += 1
        id_list = [str(r["external_id"]).strip() for r in rows if r.get("external_id")]
        stats = fetch_md_stats(id_list)

        batch_updated = 0
        batch_still_null = 0

        for row in rows:
            row_id = int(row["id"])
            ext_id = str(row.get("external_id", "")).strip()
            row_stats = stats.get(ext_id, {})
            rating_obj = (row_stats.get("rating") or {})
            raw_score = rating_obj.get("bayesian")
            if raw_score is None:
                raw_score = rating_obj.get("average")

            if raw_score is None:
                batch_still_null += 1
                last_id = row_id
                continue

            try:
                rating = round(float(raw_score) * 10.0, 2)
            except (TypeError, ValueError):
                batch_still_null += 1
                last_id = row_id
                continue

            distribution = rating_obj.get("distribution") or {}
            rating_count = 0
            for v in distribution.values():
                try:
                    rating_count += int(v)
                except (TypeError, ValueError):
                    pass

            payload = {
                "rating": rating,
                "rating_count": rating_count,
            }

            # Keep existing view_count unless it is null.
            follows = row_stats.get("follows")
            if row.get("view_count") is None and follows is not None:
                try:
                    payload["view_count"] = int(follows)
                except (TypeError, ValueError):
                    pass

            if patch_row(row_id=row_id, payload=payload):
                batch_updated += 1
            else:
                batch_still_null += 1

            last_id = row_id

        processed += len(rows)
        updated += batch_updated
        still_null += batch_still_null
        save_state(last_id)

        print(
            f"  Batch {batch_no} | processed: {len(rows)} | "
            f"rated: {batch_updated} | still null: {batch_still_null}"
        )
        time.sleep(REQUEST_DELAY)

    elapsed = round(time.time() - started, 1)
    print("\nMangaDex enrichment complete")
    print(f"  Rows processed:      {processed}")
    print(f"  Records updated:    {updated}")
    print(f"  Still null:         {still_null}")
    print(f"  Last processed id:  {last_id}")
    print(f"  Time elapsed:       {elapsed}s")


if __name__ == "__main__":
    main()
