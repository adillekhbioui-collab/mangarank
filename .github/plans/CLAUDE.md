# Claude Project Instructions

Project: ManhwaRank: The Archive
Repository root: manhwa-aggregator

Use this file as the default operating context for all chats and coding tasks in this repository.
when ever i ask for implimentation plan or context prompt for our ai agents u may consider returning a complete md file
## 1) Product Mission

ManhwaRank: The Archive is a multi-source manga intelligence platform focused on manhwa/manhua discovery.

Core user value:
- Aggregate noisy source data into trustworthy rankings.
- Support filtering and exploration by score, popularity, completion behavior, and genres.
- Keep ranking logic explainable and data quality measurable.

## 2) System Overview

Architecture flow:
1. Source fetchers write raw rows into Supabase table `manga_raw`.
2. Pipeline scripts clean, deduplicate, and aggregate data.
3. Aggregated records are upserted into `manga_rankings`.
4. FastAPI backend serves endpoints used by React frontend.

Main directories:
- `scraper/` -> source ingestion and targeted rating enrichment scripts.
- `pipeline/` -> `clean.py`, `deduplicate.py`, `aggregate.py`.
- `backend/` -> FastAPI app and API logic.
- `frontend/` -> React app and UI.

## 3) Current Business-Critical KPI

Primary KPI:
- Number of unscored titles in deduplicated output/rankings.

Definition:
- A title is unscored when all source ratings are null, causing aggregated score denominator to be zero.

Current progress snapshot from recent work:
- Baseline unscored: 11348
- Improved to: 7201

Interpretation:
- Major improvements already landed.
- Remaining tail likely contains true upstream sparse data.

## 4) Data and Scoring Logic (Do Not Break)

Aggregated score is confidence-weighted.
For each non-null source rating:
- Source has a fixed weight.
- Confidence is log(rating_count + 1), fallback 0.5 if count missing/zero.

Formula:
- numerator = sum(rating * source_weight * confidence)
- denominator = sum(source_weight * confidence)
- aggregated_score = numerator / denominator
- if denominator == 0 => aggregated_score = null

Source weights (current):
- anilist: 1.0
- mal: 0.95
- mangadex: 0.85
- kitsu: 0.7

Popularity score:
- Uses normalized per-source views against source max.
- Uses log-confidence on views.
- Kitsu popularity is intentionally weighted as 0.0 due to non-comparable view semantics.

Completion rate:
- Derived from AniList status counters.
- Only set when reader floor threshold is satisfied in pipeline logic.

## 5) Important Product Behaviors

Top categories include logic-heavy slices:
- `completion-masterpieces`: high score, high completion, sufficient readers.
- `completion-traps`: high score, low completion, large audience.
- `guilty-pleasures`: lower score, high completion, sufficient readers.

Genre relationships endpoint:
- Builds graph from genre co-occurrence counts.
- Filters weak edges and normalizes strength.

Similar manga endpoint:
- Delegates to Supabase RPC `get_similar_manga`.

## 6) Recent Engineering History (Context You Must Preserve)

Already implemented:
1. AniList fetcher fallback improved (`averageScore` -> `meanScore`).
2. Kitsu fetcher upgraded to robust rating fallbacks:
   - `averageRating` -> `bayesianRating` -> derived from `ratingFrequencies`.
3. Kitsu rating_count fallbacks improved:
   - `ratingCount` -> frequency sum -> fallback `userCount`.
4. Targeted enrichment scripts added:
   - `scraper/enrich_ratings_mangadex.py`
   - `scraper/enrich_ratings_anilist.py`
   - `scraper/enrich_ratings_mal.py`
   - `scraper/enrich_ratings_kitsu.py`
5. Orchestrator added/fixed:
   - `run_enrichment.py` executes enrichers then clean/dedup/aggregate.
6. Kitsu script timestamp updated to timezone-aware UTC.

## 7) Operational Commands

Preferred fast remediation path:
- `python run_enrichment.py`

Manual sequence:
1. `python scraper/enrich_ratings_kitsu.py`
2. `python scraper/enrich_ratings_mal.py`
3. `python scraper/enrich_ratings_anilist.py`
4. `python pipeline/clean.py`
5. `python pipeline/deduplicate.py`
6. `python pipeline/aggregate.py`

Resume semantics:
- Enrichment scripts may use local state files (`last_id`).
- "Resume from id > N" means continue from next row after N.

## 8) Guardrails for Claude

When editing this project:
1. Prefer targeted enrichment and measurable KPI improvements over broad refetches unless explicitly required.
2. Do not invent synthetic ratings for unknown titles.
3. Keep all score logic explainable and traceable to source fields.
4. Preserve existing API contracts unless requested to change them.
5. Avoid changing source weights or thresholds without documenting rationale and impact.
6. If changing dedup thresholds, quantify precision/recall tradeoff with before/after metrics.
7. For every substantial data-pipeline change, include a validation plan and KPI delta expectations.

## 9) Validation Checklist for Any Non-Trivial Change

After data or scoring changes:
1. Run pipeline end-to-end.
2. Recompute unscored counts and source-combo breakdown.
3. Verify key endpoints still respond:
   - `/manga`
   - `/top/{category}`
   - `/stats`
   - `/genres/relationships`
4. Confirm no obvious frontend regressions in filter/sort behavior.

## 10) Preferred Output Style for Claude in This Repo

For implementation chats:
- Be concrete and operational, not abstract.
- Report exact files touched and why.
- Provide command sequence and expected outcomes.
- For math or scoring changes, show formulas and examples.
- End with next best actions ranked by impact.

## 11) Priority Backlog (Current)

High impact now:
1. Continue reducing remaining unscored tail without fake imputation.
2. Add automated post-run quality report (null-rate by source and combos).
3. Improve dedup identity confidence for edge title variants.
4. Add score explainability payloads to API/frontend.
5. Add reliability automation (scheduled jobs, alerts, smoke tests).

## 12) Fast Project Primer for New Chat Sessions

If context is missing in a new chat, read these files first:
1. `PROJECT_FULL_CONTEXT.md`
2. `UNSCORED_MANGA_PLAN.md`
3. `run_enrichment.py`
4. `pipeline/aggregate.py`
5. `pipeline/deduplicate.py`
6. `backend/main.py`
7. `frontend/src/App.jsx`

Then continue work from KPI-driven priorities listed above.
