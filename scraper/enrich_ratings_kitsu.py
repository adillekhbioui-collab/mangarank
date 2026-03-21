"""
Targeted Kitsu rating enrichment.

Updates only rows in manga_raw where:
- source_site = 'kitsu'
- rating IS NULL
- external_id IS NOT NULL

Calls Kitsu per-id endpoint and PATCHes only rating columns.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
KITSU_BASE_URL = "https://kitsu.io/api/edge/manga"

REQUEST_DELAY = 0.7
BATCH_FETCH = 200
STATE_PATH = os.path.join(os.path.dirname(__file__), "enrich_ratings_kitsu.state.json")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL / SUPABASE_KEY missing in .env")
    sys.exit(1)

sb_client = httpx.Client(timeout=30, follow_redirects=True)
kitsu_client = httpx.Client(
    timeout=30,
    follow_redirects=True,
    headers={
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    },
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
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def parse_kitsu_rating(attrs: dict) -> float | None:
    for key in ("averageRating", "bayesianRating"):
        raw = attrs.get(key)
        if raw is None:
            continue
        try:
            return max(0.0, min(100.0, float(raw)))
        except (TypeError, ValueError):
            pass

    freqs = attrs.get("ratingFrequencies") or {}
    if not isinstance(freqs, dict):
        return None

    weighted = 0.0
    total = 0
    for bucket_raw, count_raw in freqs.items():
        try:
            bucket = int(str(bucket_raw))
            count = int(count_raw)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        weighted += (bucket * 5.0) * count
        total += count

    if total <= 0:
        return None

    return max(0.0, min(100.0, weighted / total))


def parse_kitsu_rating_count(attrs: dict) -> int:
    raw_count = attrs.get("ratingCount")
    if raw_count is not None:
        try:
            return max(0, int(raw_count))
        except (TypeError, ValueError):
            pass

    freqs = attrs.get("ratingFrequencies") or {}
    if isinstance(freqs, dict):
        total = 0
        for value in freqs.values():
            try:
                total += int(value)
            except (TypeError, ValueError):
                pass
        if total > 0:
            return total

    fallback = attrs.get("userCount", 0) or 0
    try:
        return max(0, int(fallback))
    except (TypeError, ValueError):
        return 0


def fetch_null_rows(last_id: int, limit: int) -> list[dict]:
    url = (
        f"{SUPABASE_URL}/rest/v1/manga_raw"
        f"?select=id,external_id"
        f"&source_site=eq.kitsu"
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


def fetch_kitsu_rating(kitsu_id: str) -> dict | None:
    url = f"{KITSU_BASE_URL}/{kitsu_id}"

    for attempt in range(3):
        try:
            r = kitsu_client.get(url)
            if r.status_code == 200:
                data = r.json().get("data") or {}
                return data.get("attributes") or {}
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", "5"))
                time.sleep(wait)
                continue
            if r.status_code in (500, 502, 503, 504):
                time.sleep(2)
                continue
            print(f"    Kitsu error {r.status_code} for id={kitsu_id}: {r.text[:160]}")
            return None
        except httpx.HTTPError:
            if attempt == 2:
                return None
            time.sleep(1)

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
    print("  Kitsu Targeted Rating Enrichment")
    print("=" * 60)
    print(f"  Resume from id > {last_id}")

    while True:
        rows = fetch_null_rows(last_id=last_id, limit=BATCH_FETCH)
        if not rows:
            break

        for row in rows:
            row_id = int(row["id"])
            kitsu_id = str(row.get("external_id", "")).strip()

            attrs = fetch_kitsu_rating(kitsu_id)
            if not attrs:
                still_null += 1
                processed += 1
                last_id = row_id
                continue

            rating = parse_kitsu_rating(attrs)
            if rating is None:
                still_null += 1
                processed += 1
                last_id = row_id
                if processed % 100 == 0:
                    print(f"  [Kitsu] {processed} processed | updated: {updated} | null: {still_null}")
                time.sleep(REQUEST_DELAY)
                continue

            rating_count = parse_kitsu_rating_count(attrs)

            payload = {
                "rating": round(float(rating), 2),
                "rating_count": rating_count,
            }

            if patch_row(row_id=row_id, payload=payload):
                updated += 1
            else:
                still_null += 1

            processed += 1
            last_id = row_id
            save_state(last_id)

            if processed % 100 == 0:
                print(f"  [Kitsu] {processed} processed | updated: {updated} | null: {still_null}")

            time.sleep(REQUEST_DELAY)

        save_state(last_id)

    elapsed = round(time.time() - started, 1)
    print("\nKitsu enrichment complete")
    print(f"  Rows processed:      {processed}")
    print(f"  Records updated:    {updated}")
    print(f"  Still null:         {still_null}")
    print(f"  Last processed id:  {last_id}")
    print(f"  Time elapsed:       {elapsed}s")


if __name__ == "__main__":
    main()
