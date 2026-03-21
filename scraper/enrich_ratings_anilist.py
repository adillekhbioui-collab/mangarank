"""
Targeted AniList rating enrichment.

Updates only rows in manga_raw where:
- source_site = 'anilist'
- rating IS NULL
- external_id IS NOT NULL

For each batch, calls AniList GraphQL with id_in and updates only rating columns.
Rating mapping matches fetch_anilist.py behavior:
- rating = averageScore or meanScore
- rating_count = popularity
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
ANILIST_URL = "https://graphql.anilist.co"

BATCH_SIZE = 50
REQUEST_DELAY = 1.2
STATE_PATH = os.path.join(os.path.dirname(__file__), "enrich_ratings_anilist.state.json")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL / SUPABASE_KEY missing in .env")
    sys.exit(1)

GQL_QUERY = """
query ($ids: [Int]) {
  Page(perPage: 50) {
    media(type: MANGA, id_in: $ids) {
      id
      averageScore
      meanScore
      popularity
    }
  }
}
"""

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
        f"?select=id,external_id"
        f"&source_site=eq.anilist"
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


def fetch_anilist_batch(ids: list[int]) -> dict[int, dict]:
    payload = {"query": GQL_QUERY, "variables": {"ids": ids}}

    for attempt in range(3):
        try:
            r = client.post(ANILIST_URL, json=payload)
            if r.status_code == 200:
                media = (((r.json() or {}).get("data") or {}).get("Page") or {}).get("media") or []
                out: dict[int, dict] = {}
                for m in media:
                    mid = m.get("id")
                    if isinstance(mid, int):
                        out[mid] = m
                return out
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", "5"))
                print(f"  AniList rate-limited. Waiting {wait}s ...")
                time.sleep(wait)
                continue
            print(f"  AniList GraphQL error {r.status_code}: {r.text[:220]}")
            return {}
        except httpx.HTTPError as e:
            if attempt == 2:
                print(f"  AniList request failed after retries: {e}")
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

    processed = 0
    updated = 0
    still_null = 0
    batch_no = 0

    print("=" * 60)
    print("  AniList Targeted Rating Enrichment")
    print("=" * 60)
    print(f"  Resume from id > {last_id}")

    while True:
        rows = fetch_null_rows(last_id=last_id, limit=BATCH_SIZE)
        if not rows:
            break

        batch_no += 1

        ids = []
        row_by_ext: dict[int, dict] = {}
        for row in rows:
            try:
                ext = int(str(row.get("external_id", "")).strip())
                ids.append(ext)
                row_by_ext[ext] = row
            except ValueError:
                continue

        gql_map = fetch_anilist_batch(ids)

        batch_updated = 0
        batch_still_null = 0

        for row in rows:
            row_id = int(row["id"])
            ext_raw = str(row.get("external_id", "")).strip()

            try:
                ext = int(ext_raw)
            except ValueError:
                batch_still_null += 1
                last_id = row_id
                continue

            media = gql_map.get(ext)
            if not media:
                batch_still_null += 1
                last_id = row_id
                continue

            raw_score = media.get("averageScore")
            if raw_score is None:
                raw_score = media.get("meanScore")

            if raw_score is None:
                batch_still_null += 1
                last_id = row_id
                continue

            try:
                rating = float(raw_score)
            except (TypeError, ValueError):
                batch_still_null += 1
                last_id = row_id
                continue

            popularity = media.get("popularity")
            try:
                rating_count = int(popularity) if popularity is not None else 0
            except (TypeError, ValueError):
                rating_count = 0

            payload = {
                "rating": rating,
                "rating_count": rating_count,
            }

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
            f"updated: {batch_updated} | still null: {batch_still_null}"
        )

        time.sleep(REQUEST_DELAY)

    elapsed = round(time.time() - started, 1)
    print("\nAniList enrichment complete")
    print(f"  Rows processed:      {processed}")
    print(f"  Records updated:    {updated}")
    print(f"  Still null:         {still_null}")
    print(f"  Last processed id:  {last_id}")
    print(f"  Time elapsed:       {elapsed}s")


if __name__ == "__main__":
    main()
