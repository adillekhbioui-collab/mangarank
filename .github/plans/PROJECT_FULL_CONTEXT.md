# Project Full Context: Manhwa Aggregator (Zero to Hero)

## 1. What We Are Building

We are building a full-stack manhwa/manhua discovery platform that:
- collects manga metadata from multiple public sources,
- normalizes and merges those records,
- computes a confidence-weighted ranking score,
- serves ranked and filterable data through an API,
- and presents it in a React frontend for exploration and discovery.

Primary product promise:
- Help users find quality titles quickly using aggregated quality signals, popularity, completion behavior, and genre exploration.

Current source APIs used:
- MangaDex
- AniList
- Kitsu
- MAL (MyAnimeList)

Core persistence:
- Supabase Postgres (via REST API)


## 2. Why This Exists

Single-source rankings are noisy and biased. Different sources have different:
- score scales,
- audience sizes,
- popularity dynamics,
- and coverage gaps.

This app combines sources into one confidence-aware score so rankings are more stable and useful than any single API list.


## 3. High-Level Architecture

Pipeline architecture:
1. Source fetchers write raw rows into `manga_raw`.
2. Processing pipeline cleans records and normalizes fields.
3. Deduplication merges cross-source entries into one title record.
4. Aggregation computes final ranking fields and upserts into `manga_rankings`.
5. FastAPI backend serves query/filter endpoints.
6. React frontend consumes backend endpoints.

Key folders:
- `scraper/`: source collectors and targeted enrichment scripts
- `pipeline/`: clean/deduplicate/aggregate transforms
- `backend/`: FastAPI service
- `frontend/`: React app


## 4. Data and Scoring Model

### 4.1 Aggregated Score Logic

Implemented in `pipeline/aggregate.py`.

Concept:
- For each source row with numeric rating, apply:
  - source weight
  - confidence term based on rating_count
- Compute weighted average.

Confidence shape:
- If `rating_count > 0`: `log(rating_count + 1)`
- Else fallback confidence of `0.5`

Important behavior:
- If all source ratings are null, denominator is 0 and `aggregated_score = null`.

This specific behavior is the root of the historical "unscored manga" problem.

### 4.2 Popularity Score Logic

Also in `pipeline/aggregate.py`.
- Normalizes source view counts against per-source maxima.
- Applies source-level popularity weights.
- Uses log-confidence for views.
- Kitsu popularity contribution is intentionally disabled in popularity weighting (`0.0`) to avoid distortion from incompatible view semantics.

### 4.3 Completion Rate

From AniList list-status counts (completed/dropped/current/paused).
- Computed only when enough readers exist (thresholded in code).
- Used for product-level slices like masterpieces and completion traps.


## 5. Backend API Surface (Current)

From `backend/main.py`, the API provides:
- `GET /manga` for list, filters, sorting, and pagination
- `GET /manga/{title}` for detail page
- `GET /genres`
- `GET /top/{category}`
- `GET /stats`
- Similar/analysis-style endpoints and genre relationship features are present in the backend logic

Backend implementation notes:
- Async `httpx` client with app lifespan management
- CORS enabled broadly
- In-memory TTL caching for expensive responses
- Genre relationship graph computation with co-occurrence filtering
- Reads/writes through Supabase REST (`/rest/v1/...`)


## 6. Frontend Product Surface (Current)

From `frontend/src/App.jsx` and related components:
- Search and browse experience with URL-synced filters
- Sort modes: score, views, chapters, completion
- Status and chapter constraints
- Include/exclude genre filters with tri-state behavior
- Quick filter categories (masterpieces, hard-to-finish, etc.)
- Top category panels and detail routes
- Genre universe chart section component exists

UX/product pattern:
- Exploration-first browsing with strong filter ergonomics
- Stable query-state in URL for sharing and re-entry


## 7. Major Problem We Worked Through: Unscored Manga

## 7.1 Problem Definition

"Unscored" means a deduplicated title has no non-null rating from any source, so aggregation returns null.

## 7.2 Baseline Before Fixes

Measured on deduplicated data:
- `total_titles = 24466`
- `unscored_titles = 11348`

Main unscored source combos (largest):
- anilist-only
- kitsu-only
- anilist+mal
- anilist+kitsu

Source null-rate was especially high for:
- Kitsu (worst ratio)
- AniList (largest absolute contributor)

## 7.3 Strategy Chosen

Instead of frequent full refetches (slow, expensive, operationally heavy), we built targeted enrichment:
- query rows where `rating IS NULL` for a given source,
- fetch only missing score data from that source API,
- patch only those rows,
- resume safely from checkpoints.

This gave faster iteration and measurable gains.


## 8. Concrete Fixes Implemented

### 8.1 AniList Fetcher Improvement

File: `scraper/fetch_anilist.py`

Implemented:
- Added `meanScore` field to GraphQL query.
- Fallback mapping: use `averageScore`, else `meanScore`.

Impact:
- Reduced avoidable null ratings where `averageScore` was absent but `meanScore` existed.

### 8.2 Kitsu Fetcher Improvement

File: `scraper/fetch_kitsu.py`

Implemented robust fallback parsing:
- rating: `averageRating` -> `bayesianRating` -> derived from `ratingFrequencies`
- rating_count: `ratingCount` -> sum of `ratingFrequencies` -> fallback `userCount`

Impact:
- Better score recovery for Kitsu rows that were previously left null due to strict single-field parsing.

### 8.3 Targeted Enrichment Scripts Added

New scripts in `scraper/`:
- `enrich_ratings_mangadex.py`
- `enrich_ratings_anilist.py`
- `enrich_ratings_mal.py`
- `enrich_ratings_kitsu.py`

Shared behavior:
- Only process source rows with null rating
- Update by DB row id (safe patch target)
- Track progress in local state file (`last_id`) for resume
- Print summary metrics (processed / updated / still-null / elapsed)

### 8.4 Enrichment Orchestration

File: `run_enrichment.py`

Runs in order:
1. all enrichment scripts
2. `pipeline/clean.py`
3. `pipeline/deduplicate.py`
4. `pipeline/aggregate.py`

Purpose:
- one-command refresh cycle from raw null remediation to final rankings table.

### 8.5 Reliability / Warning Cleanup

File: `scraper/enrich_ratings_kitsu.py`

Fixed deprecated UTC usage:
- replaced `datetime.utcnow()` with timezone-aware UTC (`datetime.now(timezone.utc)`).


## 9. Verified Progress So Far

Observed improvement from user runs:
- unscored titles dropped from `11348` -> `7201`

Interpretation:
- Strategy is working and has already removed thousands of null-score titles.

Additional observed state:
- A recent AniList enrichment pass processed remaining AniList-null candidates but updated 0 rows, indicating many remaining AniList nulls are truly null upstream.


## 10. Operational Runbook

### 10.1 Preferred Iteration Loop (Fast)

1. Run targeted enrichment orchestrator:
   - `python run_enrichment.py`
2. Re-profile unscored counts.
3. Inspect which source combos still dominate.
4. Improve source-specific extraction where possible.

### 10.2 Individual Script Execution

Examples:
- `python scraper/enrich_ratings_kitsu.py`
- `python scraper/enrich_ratings_mal.py`
- `python scraper/enrich_ratings_anilist.py`

### 10.3 Resume Semantics

State files store last processed id.
- "Resume from id > N" means continue from next unprocessed row.
- Delete/edit state file to force re-run from start.

### 10.4 Full Fetch Path (Slower)

Use full source fetchers when schema changes or major refresh is needed:
- `fetch_mangadex.py`
- `fetch_anilist.py`
- `fetch_kitsu.py`
- MAL fetcher if used in this repo version

Then run full pipeline.


## 11. Product Decisions and Conventions

Important conventions currently used:
- Ratings normalized on 0-100 scale during pipeline
- Source weights are explicit constants in aggregation
- Null rating rows are not forced into fake defaults
- Kitsu popularity is excluded from popularity score weighting
- Ranking records upsert by title conflict key in current pipeline

Design intent:
- Prefer data honesty (null when truly unknown) over fabricated certainty.


## 12. Known Gaps / Risks

1. Upstream sparsity remains for long-tail titles.
2. Dedup quality directly affects score rescue (if same title fails to merge, one source may not help another).
3. Upsert-by-title can be brittle for title variants/transliteration edge cases.
4. Some sources may expose score fields with partial regional or format coverage.
5. Remaining unscored set may increasingly be true cold-start titles.


## 13. Future Vision (Where To Take This)

### 13.1 Data Quality and Scoring

1. Add automated post-run coverage report:
   - per-source non-null rating percentage
   - source combo distribution for unscored titles
   - week-over-week drift

2. Add confidence metadata surfaced to frontend:
   - number of contributing sources
   - effective confidence weight
   - data freshness timestamp

3. Move from title-only upsert identity to stronger canonical id mapping table.

4. Add optional Bayesian shrinkage / prior blending to stabilize low-sample ratings.

### 13.2 Product Experience

1. Expose "Why this rank" explainer in UI:
   - source contributions
   - confidence factors
   - completion and popularity components

2. Add personalized discovery:
   - genre preference profiles
   - similarity and serendipity controls

3. Add ranking slices:
   - hidden gems (high completion, medium popularity)
   - high-risk high-reward (high score, low completion)
   - momentum (recently rising titles)

### 13.3 Platform Reliability

1. Add scheduled jobs and run-level telemetry.
2. Add failure alerts on fetch/enrichment regressions.
3. Add smoke tests for critical API endpoints after each pipeline run.


## 14. Context Timeline (What Happened, In Order)

1. Diagnosed unscored issue in aggregation behavior.
2. Baseline profiling quantified severity (`11348` unscored).
3. Added AniList `meanScore` fallback support.
4. Authored recovery plan doc (`UNSCORED_MANGA_PLAN.md`).
5. Shifted from full refetch strategy to targeted null-only enrichment.
6. Implemented enrichment scripts for MangaDex, AniList, MAL.
7. Added/maintained orchestrator for enrichment + pipeline.
8. Measured significant improvement (`7201` unscored).
9. Investigated Kitsu nulls and improved Kitsu extraction logic.
10. Added Kitsu enrichment script and warning cleanup.
11. Confirmed AniList residual pass had no further recoverable updates.
12. Current focus: continue reducing remaining true-null tails and improve explainability + quality instrumentation.


## 15. Quick Start For Any New Agent

If you are a new AI agent entering this project, do this first:

1. Read these files in order:
   - `README.md`
   - `UNSCORED_MANGA_PLAN.md`
   - `run_enrichment.py`
   - `pipeline/aggregate.py`
   - `backend/main.py`
   - `frontend/src/App.jsx`

2. Understand current KPI:
   - primary KPI: count of unscored titles
   - secondary KPI: source null-rate and combo distribution

3. Run the current fast path:
   - targeted enrichment
   - pipeline rebuild
   - KPI re-profile

4. Prioritize work that:
   - reduces true nulls without fake imputation,
   - improves dedup identity quality,
   - and increases transparency of ranking confidence in UI/API.


## 16. Single-Sentence Project Summary

This project is a multi-source manga intelligence platform that transforms noisy public API data into trustworthy, explainable rankings and discovery experiences, with active work focused on eliminating null-score blind spots through targeted enrichment and stronger data quality tooling.


## 17. Deep Technical History: Exactly What Was Done

This section records the implementation sequence at engineering-detail level.

### Phase A: Root-Cause Identification

What we discovered:
1. Null rankings were not caused by a crash or arithmetic exception.
2. Null rankings were a direct, intentional outcome of scoring logic when no source had a numeric rating.
3. The highest-impact null contributors were AniList and Kitsu.

Why this mattered:
- Fixing aggregation code itself would not solve most nulls.
- We needed to increase upstream rating availability and recovery.

### Phase B: Baseline Measurement and Segmentation

Baseline measured:
- total deduplicated titles: 24466
- unscored titles: 11348

Segmented by source combination and source null-rate to identify where effort would produce highest delta.

Outcome:
- AniList had the largest absolute null impact.
- Kitsu had the highest null ratio.

### Phase C: AniList Fetcher Improvement

Change:
- Added `meanScore` fallback when `averageScore` is null.

Reasoning:
- AniList frequently has one score field null while another is populated.

Result type:
- deterministic mapping enhancement (no heuristic imputation).

### Phase D: Targeted Enrichment Framework (instead of full refetch)

What was implemented:
1. Source-specific enrichment scripts that only target rows where `rating IS NULL`.
2. Record updates by stable row `id` to avoid title collision mistakes.
3. Checkpoint state (`last_id`) for resumable runs.
4. Unified orchestrator to chain enrichment and full ranking rebuild.

Why this was chosen:
- Much faster than full source re-ingestion.
- Safer for iterative debugging.
- Allows source-by-source progress attribution.

### Phase E: Kitsu Null Recovery Improvements

Fetcher logic was upgraded from single-field extraction to fallback tree:
- `averageRating` -> `bayesianRating` -> weighted reconstruction via `ratingFrequencies`.

Count extraction was upgraded similarly:
- `ratingCount` -> frequency sum -> fallback `userCount`.

Also completed:
- timezone-safe timestamp fix in Kitsu enrichment script (removed deprecated utcnow usage).

### Phase F: Orchestration Hardening

`run_enrichment.py` was stabilized to run:
1. all enrichers,
2. clean,
3. deduplicate,
4. aggregate.

This became the standard one-command operational loop.

### Phase G: Verified KPI Movement

Measured progress:
- unscored count reduced from 11348 to 7201.

Interpretation:
- targeted enrichment strategy materially works.
- remaining tail is increasingly "true sparse" rather than parser omission.


## 18. Mathematical Logic for Complex Features

This section formalizes each complex feature so future agents can reason rigorously.

### 18.1 Rating Normalization (Cleaning Stage)

Let raw rating for source $s$ be $r_s$.

Normalized rating $r'_s$:
$$
r'_s =
\begin{cases}
10 \cdot r_s & \text{if } s = \text{mangadex} \\
r_s & \text{if } s \in \{\text{anilist}, \text{kitsu}, \text{mal}\} \\
	ext{null} & \text{if parse fails}
\end{cases}
$$

Then clamp:
$$
r'_s \leftarrow \min(100, \max(0, r'_s)).
$$

Auxiliary null fixing:
- `view_count = 0` if null/unparseable.
- `rating_count = 0` if null/unparseable.


### 18.2 Three-Layer Deduplication Logic

Data structure:
- Union-Find (Disjoint Set Union) over cleaned records.

Goal:
- Build connected components where each component is one canonical title cluster.

Layer 1: exact ID graph merge
- Build tokens like `source:external_id` and MAL cross-links.
- Union records sharing same bridge identifiers.

Layer 2: alt-title matching
1. exact alt-title overlap (cross-source only), then
2. fuzzy match across blocked candidates using threshold $\tau_{alt} = 92$.

Layer 3: primary-title fuzzy fallback
- blocked comparisons on first character and length bucket.
- fuzzy threshold $\tau_{title} = 85$.

Similarity function:
$$
	ext{match}(a,b) \iff \text{fuzz.ratio}(a,b) \ge \tau
$$

Complexity control:
- blocking keys reduce quadratic pair explosion.


### 18.3 Canonical Merge Resolution

For a cluster $C$ of records:
- canonical title: source-priority selection with English-likelihood preference.
- author: source-priority non-empty value.
- chapter count: $\max$ over cluster.
- genres: union-set, title-cased and sorted.
- status:
$$
	ext{status}(C) =
\begin{cases}
	ext{completed} & \text{if all statuses in } C \text{ are completed} \\
	ext{ongoing} & \text{otherwise}
\end{cases}
$$


### 18.4 Aggregated Score Formula

For title $m$ with source records $i \in S_m$.

Given:
- normalized rating $r_i$,
- source weight $w_i$,
- rating count $n_i$.

Confidence:
$$
c_i =
\begin{cases}
\log(n_i + 1) & \text{if } n_i > 0 \\
0.5 & \text{otherwise}
\end{cases}
$$

Aggregated score:
$$
	ext{Score}(m)=
\frac{\sum_{i \in S_m,\ r_i \neq null} r_i w_i c_i}
{\sum_{i \in S_m,\ r_i \neq null} w_i c_i}
$$

If denominator is 0:
$$
	ext{Score}(m) = null.
$$

Current source weights:
- AniList: 1.00
- MAL: 0.95
- MangaDex: 0.85
- Kitsu: 0.70


### 18.5 Popularity Score Formula

For each source $s$:
- per-title views $v_s$,
- source max views across corpus $V_{s,max}$,
- source popularity weight $W_s$.

Normalized source popularity:
$$
P_s = \frac{v_s}{V_{s,max}}.
$$

Confidence-weighted numerator:
$$
N = \sum_s P_s W_s \log(v_s + 1).
$$

Normalizer denominator:
$$
D = \sum_s W_s \log(V_{s,max} + 1).
$$

Final popularity score:
$$
	ext{Popularity}(m)=
\begin{cases}
100 \cdot N/D & \text{if } D > 0 \\
0 & \text{if } D \le 0
\end{cases}
$$

Important design choice:
- Kitsu popularity weight is currently 0 to avoid mixing incompatible traffic semantics.


### 18.6 Completion Rate Formula

From AniList reader state counts:
- completed, dropped, current, paused.

Total readers:
$$
R = completed + dropped + current + paused.
$$

Completion rate (only when reader floor is met):
$$
	ext{CompletionRate} = 100 \cdot \frac{completed}{R}.
$$

If reader floor not met:
- completion_rate is null.


### 18.7 Category Logic as Predicates

Backend top-category filters are logical predicates over ranking table fields.

Examples:
- Completion Masterpieces:
$$
	ext{aggregated\_score} \ge 75 \land
	ext{completion\_rate} \ge 60 \land
	ext{total\_readers} \ge 1000
$$

- Completion Traps:
$$
	ext{aggregated\_score} \ge 75 \land
	ext{completion\_rate} < 35 \land
	ext{total\_readers} \ge 2000
$$

- Guilty Pleasures:
$$
	ext{aggregated\_score} < 70 \land
	ext{completion\_rate} \ge 65 \land
	ext{total\_readers} \ge 1000
$$


### 18.8 Genre Relationship Graph Math

For each manga, take unique sorted genre set $G_m$.

For each unordered pair $(a,b)$ in combinations of $G_m$:
- increment edge co-occurrence count $C_{ab}$.

Keep edges with count threshold (currently $C_{ab} \ge 10$), then scale edge strength:
$$
	ext{strength}_{ab} = \frac{C_{ab}}{\max_{x,y} C_{xy}}.
$$

Node average score:
$$
	ext{avgScore}(g)=\frac{1}{|M_g|}\sum_{m \in M_g} \text{aggregated\_score}(m)
$$
where $M_g$ is manga containing genre $g$.


### 18.9 Similar Manga Logic

`/similar-manga/{title}` and `/manga/{title}/similar` delegate to Supabase RPC `get_similar_manga`.

Current backend behavior:
- same target title input
- fixed result limit (6)
- cached response key per title for low latency

The exact ranking expression is implemented in SQL RPC layer, not in Python backend code.


### 18.10 Caching Logic

For in-memory endpoint cache with TTL $T$:
$$
	ext{cache hit} \iff (t_{now} - t_{stored}) < T.
$$

Current notable TTLs:
- API in-memory cache: 10 min default
- Browser cache headers vary by endpoint (5 min, 10 min, 24h)
- Genre relationships internal refresh: 24h


## 19. Null-Rating Enrichment Algorithm (Formal)

For source $s$:

1. Query set
$$
Q_s = \{row \in manga\_raw \mid row.source\_site=s \land row.rating=null \land row.id>last\_id\}
$$

2. For each row in ascending id:
- call source API using source identifier/external id
- parse best available rating with source-specific fallback tree
- if parsed rating valid, patch DB row by id

3. Update checkpoint:
- `last_id = current_row_id`

4. Emit summary metrics:
- processed
- updated
- still_null
- elapsed_seconds

Why this is robust:
- idempotent, resumable, low blast-radius, source-isolated diagnostics.


## 20. Data Integrity Invariants

The current system is designed around these invariants:

1. No synthetic ratings are invented when all upstream values are absent.
2. Every aggregated score must be traceable to one or more source rows.
3. Enrichment scripts only patch explicit null targets.
4. Dedup clusters preserve source-level rating inputs for downstream explainability.
5. Cleaning enforces bounded numeric ranges and non-negative count fields.


## 21. Exact Current State (As of Latest Work)

1. Core ETL path is operational.
2. Enrichment framework for MangaDex, AniList, MAL, Kitsu exists and runs.
3. AniList fallback improvements are in place.
4. Kitsu rating extraction is now multi-fallback and more resilient.
5. One-command orchestrator is available for refresh loops.
6. Unscored KPI already improved significantly (11348 -> 7201).
7. Remaining tail increasingly consists of genuine upstream missing scores.


## 22. What A Future Agent Should Optimize Next

1. Instrumentation first:
- Produce automatic before/after KPI report each run.

2. Dedup precision:
- Reduce false splits and false merges with stronger canonical identity rules.

3. Explainability:
- expose score decomposition in API and UI (per-source contribution vectors).

4. Cold-start policy:
- define explicit product handling for true-null titles (display state, ranking placement, badges).

5. Reliability:
- schedule enrichment, add alerts, and add post-run endpoint smoke tests.
