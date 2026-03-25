# ManhwaRank Full Build Handoff (From Zero to Current)

Version: 2026-03-24
Scope: End-to-end project context for a new AI agent joining in a separate conversation.

---

## 1) Purpose of This Document

This file is a high-fidelity memory handoff for another AI agent.

It is designed to answer:
1. What this product is.
2. How it was built from scratch.
3. What was implemented in each phase.
4. What is currently working.
5. What known pitfalls exist in production/dev.
6. What the next agent should read, run, and verify first.

---

## 2) Project Identity

Product name: ManhwaRank

Core idea:
A multi-source manhwa/manhua discovery platform that aggregates data from multiple APIs, deduplicates titles, computes confidence-aware ranking metrics, and serves a searchable/filterable web app.

Primary user value:
1. Better ranking quality than any single source.
2. Discovery workflows (search, quick categories, genre map, similar titles).
3. Operational/admin visibility over data quality and user behavior.

---

## 3) Current Tech Stack

## 3.1 Data + Backend

- Python backend: FastAPI
- HTTP client: httpx (async)
- Database/API layer: Supabase PostgREST
- Runtime: Uvicorn
- Data processing libs: pandas, rapidfuzz
- Image processing for proxy endpoint: Pillow

Main backend dependencies (requirements):
- fastapi
- uvicorn[standard]
- httpx
- python-dotenv
- rapidfuzz
- pandas
- Pillow

## 3.2 Frontend

- React 19
- Vite 6
- React Router (BrowserRouter)
- motion (animation)
- d3 (genre relationship visualization)

---

## 4) Repository and Architecture Map

Workspace root contains multiple directories; active project is:
- manhwa-aggregator/

Major internal modules:
1. scraper/
   - Source fetchers + null-rating enrichment scripts.
2. pipeline/
   - clean -> deduplicate -> aggregate transformations.
3. backend/
   - FastAPI API service for frontend and analytics ingestion.
4. frontend/
   - React/Vite user-facing app + admin dashboard.
5. top-level utility scripts
   - setup/update/backfill/reporting helpers.

End-to-end data flow:
1. Source fetchers write to manga_raw.
2. pipeline/clean.py normalizes values.
3. pipeline/deduplicate.py merges cross-source records.
4. pipeline/aggregate.py computes ranking metrics and upserts manga_rankings.
5. backend/main.py serves query endpoints from Supabase tables.
6. frontend consumes backend APIs.

---

## 5) Chronological Build History (Zero -> Current)

## Phase 0: Foundation Setup

Initial baseline:
1. Supabase-backed storage with manga_raw and manga_rankings.
2. Scrapers for MangaDex, AniList, Kitsu (later MAL support in flow).
3. Pipeline scripts established for clean/deduplicate/aggregate.
4. FastAPI backend endpoints for listing/filtering manga.
5. React frontend for browsing/searching.

## Phase 1: Data Quality + Ranking Maturity

Major upgrades:
1. Confidence-weighted aggregated scoring in aggregate pipeline.
2. Popularity scoring logic with source normalization.
3. Completion-rate logic (AniList reader-state based).
4. Deduplication system improved using three-layer matching:
   - external/cross IDs,
   - alternative titles,
   - fuzzy title fallback.

## Phase 2: Unscored Manga Remediation

Problem discovered:
- Many titles had null aggregated_score because all source ratings were null.

Measured baseline:
- 24,466 deduplicated titles
- 11,348 unscored titles

Implemented strategy:
- Null-only targeted enrichment scripts per source, resumable with state files.

Implemented scripts:
1. scraper/enrich_ratings_mangadex.py
2. scraper/enrich_ratings_anilist.py
3. scraper/enrich_ratings_mal.py
4. scraper/enrich_ratings_kitsu.py

Operational orchestrator:
- run_enrichment.py now runs:
  1) all enrichers
  2) clean
  3) deduplicate
  4) aggregate

Observed impact:
- unscored dropped from 11,348 -> 7,201.

## Phase 3: UX/Product Expansion

Frontend expanded with:
1. URL-synced search/filter state.
2. Tri-state genre include/exclude behavior.
3. Quick category tabs (masterpieces, traps, action, etc.).
4. Manga detail page with similar titles and watchlist interaction.
5. Genre relationship visualization section.
6. Theme support and mobile interaction polish.

## Phase 4: Analytics and Admin Control Room

Added two analytics channels:
1. Umami script-based analytics (self-hosted Umami).
2. Persisted event analytics in backend/Supabase via POST /analytics/events.

Persisted events include:
- search
- manga_click
- manga_view
- filter_applied
- watchlist_add
- watchlist_remove

Added admin backend endpoints requiring X-Admin-Password:
1. /admin/stats
2. /admin/source-health
3. /admin/score-distribution
4. /admin/coverage
5. /admin/analytics/searches
6. /admin/analytics/manga-views
7. /admin/analytics/filters
8. /admin/analytics/watchlist

Added frontend admin page:
- /admin route
- password gate stored in sessionStorage
- dashboard panels with per-widget error handling
- Umami iframe section

## Phase 5: Deployment Hardening and Production Issues

Deployment model:
- Backend on Render
- Frontend on Vercel
- Umami as separate service on Render

Issues encountered and solved:
1. Vercel direct-route 404 on /admin
   - Cause: BrowserRouter without SPA rewrite.
   - Fix: frontend/vercel.json rewrite to /index.html.

2. Admin widgets returning HTTP 503
   - Cause: ADMIN_PASSWORD missing in backend env.
   - Fix: set ADMIN_PASSWORD in Render and redeploy.

3. Umami iframe not loading/refused to connect
   - Cause: Umami framing policy not configured.
   - Fix: set Umami ALLOWED_FRAME_URLS and rebuild Umami service.

4. Top Searched Titles panel showing fetch error
   - Immediate runtime cause (confirmed): Brave Shields blocked analytics request.
   - Resolution: disable/adjust Brave Shields for site/API domain.

---

## 6) Current API Surface (Backend)

Main public endpoints:
1. GET /manga
2. GET /manga/{title}
3. GET /manga/{title}/similar
4. GET /similar-manga/{title}
5. GET /genres
6. GET /genres/blacklist
7. GET /genres/relationships
8. GET /top/{category}
9. GET /stats
10. GET /proxy/image
11. POST /analytics/events

Admin endpoints (password-guarded):
1. GET /admin/stats
2. GET /admin/source-health
3. GET /admin/score-distribution
4. GET /admin/coverage
5. GET /admin/analytics/searches
6. GET /admin/analytics/manga-views
7. GET /admin/analytics/filters
8. GET /admin/analytics/watchlist

Security gate behavior:
- If ADMIN_PASSWORD env missing: returns 503 "Admin endpoints are not configured."
- If header mismatch: returns 401 Unauthorized.

---

## 7) Current Frontend Surface

Core routes and pages:
1. Home/browse page
2. Manga detail page
3. Admin page (/admin)

Frontend platform characteristics:
1. BrowserRouter is used (requires SPA host rewrite for deep links).
2. API base is env-driven with local fallback:
   - VITE_API_BASE_URL or http://localhost:8000
3. Admin API calls use X-Admin-Password header.
4. Widget-level fetch failures are isolated and rendered as panel errors.

Analytics integration:
1. Umami script loaded in frontend/index.html.
2. useAnalytics hook sends event to Umami and optionally persists event to backend.
3. Persisted event payload supports metadata/filter_state/manga_title/genre/session_id.

---

## 8) Data and Scoring Logic (Current)

## 8.1 Aggregated Score

Weighted confidence average across available source ratings.

Inputs per source row:
1. rating
2. source weight
3. rating_count

Confidence term:
- log(rating_count + 1) when rating_count > 0
- fallback confidence 0.5 otherwise

If no source has rating, aggregated_score remains null.

Current source score weights:
- anilist: 1.00
- mal: 0.95
- mangadex: 0.85
- kitsu: 0.70

## 8.2 Popularity Score

Derived from normalized source views and confidence weighting.

Design decision:
- kitsu popularity weight is 0.0 in popularity computation to avoid semantic distortion.

## 8.3 Completion Rate

Computed using AniList reader state counts when total_readers threshold is met.
Stored in manga_rankings as:
1. completion_rate
2. total_readers

## 8.4 Deduplication

Three-layer merge strategy:
1. Cross-reference IDs/bridges
2. Alt-title matching
3. Fuzzy primary-title matching

Output is canonical merged record with source_ratings retained for aggregation.

---

## 9) Deployment and Environment Contracts

## 9.1 Render Backend Required Env

1. SUPABASE_URL
2. SUPABASE_KEY
3. ADMIN_PASSWORD
4. Optional: ALLOWED_ORIGINS (comma-separated)

Without ADMIN_PASSWORD, admin endpoints intentionally fail with 503.

## 9.2 Vercel Frontend Required Env

1. VITE_API_BASE_URL
2. VITE_UMAMI_SHARE_URL (for embedded Umami iframe widget)

Important:
- Vite env vars are build-time; after changing env values, redeploy frontend.

## 9.3 SPA Routing Requirement

Because BrowserRouter is used, frontend/vercel.json includes rewrite:
- all routes -> /index.html

Without this, direct /admin URL can return 404 on Vercel.

## 9.4 Umami Service Notes

Umami is deployed as a separate service, not inside app repo runtime.
For iframe embedding, Umami frame allowlist (ALLOWED_FRAME_URLS) must include app origin and requires Umami rebuild/redeploy.

---

## 10) Operational Runbooks

## 10.1 Local Development

From manhwa-aggregator:
1. activate venv
2. install backend deps from requirements.txt
3. run backend: uvicorn backend.main:app --reload --port 8000

From frontend:
1. npm install
2. npm run dev

## 10.2 Data Refresh / Enrichment Loop

Preferred command:
- python run_enrichment.py

This executes null-rating enrichment scripts then full transformation pipeline.

## 10.3 Production Deploy Workflow

Recommended path:
1. create feature branch
2. commit and push branch
3. open PR into main
4. merge after checks
5. Render/Vercel auto-deploy from main

---

## 11) Known Pitfalls and Resolved Incidents

1. Browser tracker blocking can break analytics/admin widgets in client browser.
   - Example confirmed: Brave Shields blocked Top Searched Titles request.

2. Wrong env file location for Vite vars can make frontend think vars are missing.
   - VITE_* must exist in frontend environment scope.

3. Preview deployment confusion on Vercel can make production appear stale.
   - Ensure target deployment is promoted/active for production domain.

4. Dirty git staging may accidentally include .venv binaries and pyc artifacts.
   - Must keep virtual env/cache/build outputs out of commits.

---

## 12) Current State Snapshot (As of This Handoff)

Working:
1. Public site browsing/filtering/detail flows.
2. /admin route is publicly reachable (no more 404 when rewrite is active).
3. Admin auth gate and most admin panels functioning.
4. Umami integration and embedded dashboard flow are configured.
5. Backend admin endpoints active when ADMIN_PASSWORD is set.

Recently confirmed issue and fix:
- Top Searched Titles error was caused by Brave Shields, not backend logic.

Potential improvement to consider later:
- Search event payload currently sends query at top-level in one flow, while admin searches endpoint reads metadata.query. Consider normalizing payload and adding backward-compatible server fallback if needed.

---

## 13) Recommended Reading Order for Next AI Agent

Read in this sequence:
1. manhwa-aggregator/README.md
2. manhwa-aggregator/PROJECT_FULL_CONTEXT.md
3. manhwa-aggregator/run_enrichment.py
4. manhwa-aggregator/pipeline/deduplicate.py
5. manhwa-aggregator/pipeline/aggregate.py
6. manhwa-aggregator/backend/main.py
7. manhwa-aggregator/frontend/src/App.jsx
8. manhwa-aggregator/frontend/src/components/admin/AdminDashboard.jsx
9. manhwa-aggregator/frontend/src/api.js
10. manhwa-aggregator/frontend/src/hooks/useAnalytics.js
11. manhwa-aggregator/frontend/src/utils/logEvent.js
12. manhwa-aggregator/frontend/vercel.json

---

## 14) Fast Verification Checklist for New Agent

Backend checks:
1. GET /stats returns valid JSON.
2. GET /genres returns genre list.
3. Admin endpoint with wrong password returns 401.
4. Admin endpoint with missing ADMIN_PASSWORD returns 503 (expected safety behavior).
5. Admin endpoint with correct password returns data.

Frontend checks:
1. Home loads and fetches manga list from VITE_API_BASE_URL.
2. Direct /admin load works in production (rewrite active).
3. Admin login unlocks dashboard widgets.
4. Umami iframe appears when VITE_UMAMI_SHARE_URL is set.
5. Top Searched Titles tested with browser shields/adblock disabled for domain.

Data checks:
1. run_enrichment.py completes end to end.
2. manga_rankings updated_at changes after run.
3. unscored KPI measured and trended over time.

---

## 15) Prioritized Next Steps (If Continuing Development)

1. Analytics robustness:
   - Normalize search event payload schema and add compatibility fallback.

2. Data quality instrumentation:
   - Add automatic post-run KPI report (unscored totals, source null rates, combo distribution).

3. Explainability:
   - Surface score contribution and confidence metadata in API/UI.

4. Deployment reliability:
   - Add smoke checks after deploy for /stats and core admin endpoints.

5. Dedup quality:
   - Improve canonical identity mapping beyond title-based conflict handling.

---

## 16) One-Paragraph Executive Summary for Any Agent

ManhwaRank is a full-stack multi-source manga intelligence app built on Supabase, FastAPI, and React/Vite. The team progressed from basic scraping and ranking into a mature pipeline with three-layer deduplication, confidence-weighted scoring, completion/popularity features, and targeted null-rating enrichment that significantly reduced unscored titles. The product now includes an admin control room with protected analytics endpoints, persisted event analytics, and Umami integration. Key production lessons were SPA routing rewrites for BrowserRouter, strict environment setup on Render/Vercel, and browser shield/adblock interference with analytics requests. The codebase is operational and ready for optimization work focused on analytics schema consistency, KPI instrumentation, and ranking explainability.
