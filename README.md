# Manhwa & Manhua Discovery & Ranking App

A web application for browsing, filtering, and discovering the best manhwa (Korean comics) and manhua (Chinese comics), ranked by a unified confidence-weighted score computed from three independent public APIs.

## Folder Structure

```
manhwa-aggregator/
├── scraper/        # API fetch scripts (MangaDex, AniList, Kitsu)
├── pipeline/       # Data processing scripts (clean, deduplicate, aggregate)
├── backend/        # FastAPI REST API server
├── .env            # Environment variables (Supabase credentials)
├── README.md       # This file
└── requirements.txt
```

### `scraper/`
Contains three Python scripts that fetch raw manga data from public APIs and write it to the `manga_raw` table in Supabase:
- **`fetch_mangadex.py`** — Fetches titles, chapters, covers, and tags from the MangaDex API
- **`fetch_anilist.py`** — Fetches scores, popularity rankings, and genres from AniList GraphQL
- **`fetch_kitsu.py`** — Fetches supplementary ratings and metadata from the Kitsu API

### `pipeline/`
Contains processing scripts that transform raw data into clean, ranked results:
- **`clean.py`** — Normalize scores to 0–100, fix types, remove invalid records
- **`deduplicate.py`** — Fuzzy-match titles across sources (85% threshold), merge into one record per manga
- **`aggregate.py`** — Apply confidence-weighted scoring formula, write final rankings
- **`run_pipeline.py`** — Orchestrator that runs all three steps in sequence

### `backend/`
Contains the FastAPI application that serves ranked manga data to the frontend:
- `GET /manga` — Filtered list with pagination
- `GET /manga/{title}` — Full detail for one manga
- `GET /genres` — All unique genres in the database
- `GET /top/{category}` — Top 20 for action, romance, fantasy, drama, etc.
- `GET /stats` — Total count, source count, top genres, last updated

## Data Sources

| API | Auth Required | Best For |
|-----|---------------|----------|
| **MangaDex API** | None | Titles, chapters, cover images, tags |
| **AniList GraphQL** | None | Scores, popularity rankings, genres |
| **Kitsu API** | None | Supplementary ratings and metadata |

## Tech Stack

- **Data Fetching**: Python (`httpx`)
- **Data Processing**: Python (`pandas`, `rapidfuzz`)
- **Database**: Supabase (PostgreSQL)
- **Backend**: FastAPI + Uvicorn
- **Frontend**: React (separate repo/folder)
- **Hosting**: Railway (backend) + Vercel (frontend)

## Getting Started

1. Activate the virtual environment:
   ```bash
   # Windows
   .venv\Scripts\activate
   ```
2. Fill in `.env` with your Supabase credentials
3. Run the API fetchers: `python scraper/fetch_mangadex.py` (etc.)
4. Run the pipeline: `python pipeline/run_pipeline.py`
5. Start the backend: `uvicorn backend.main:app --reload`
