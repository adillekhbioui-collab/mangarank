# Unscored Manga Recovery Plan

## Goal
Reduce the number of titles with `score = null` ("unscored") in the aggregated rankings.

## Problem Definition
A manga becomes unscored when all source ratings for that deduplicated title are `null`.

Scoring behavior is implemented in `pipeline/aggregate.py`:
- `compute_score(...)` skips source rows where `rating is None`
- if weighted denominator stays `0`, function returns `None`

## Baseline Snapshot (Before Fixes)
From profiling `pipeline/deduplicated.json`:

- total_titles: `24466`
- unscored_titles: `11348`

Top unscored source combinations:
1. (`anilist`) -> `6816`
2. (`kitsu`) -> `2462`
3. (`anilist`, `mal`) -> `1016`
4. (`anilist`, `kitsu`) -> `583`
5. (`mal`) -> `248`
6. (`kitsu`, `mal`) -> `118`
7. (`anilist`, `kitsu`, `mal`) -> `104`
8. (`kitsu`, `mangadex`) -> `1`

Null-rate by source:
- anilist: `0.6514`
- kitsu: `0.8051`
- mal: `0.5185`
- mangadex: `0.0001`

Null rows inside unscored titles:
- anilist: `8527`
- kitsu: `3274`
- mal: `1488`
- mangadex: `1`

## Work Completed

### 1) MAL coverage and stability fixes
File: `scraper/fetch_mal.py`

Implemented:
- switched fetch strategy from broad ranking filtering to direct subtype crawl (`manhwa`, `manhua`)
- enabled redirect following for HTTP client (`follow_redirects=True`)

Why:
- previous approach under-fetched MAL records and occasionally failed due redirects

Expected impact:
- improved MAL record coverage and fewer MAL-related missing-rating cases over full runs

### 2) AniList rating fallback fix
File: `scraper/fetch_anilist.py`

Implemented:
- added `meanScore` to GraphQL query
- updated rating mapping logic:
  - use `averageScore` first
  - fallback to `meanScore` when `averageScore` is null
  - safe float parsing with null guard

Why:
- large `anilist-only` unscored bucket indicated many records had no `averageScore`

Expected impact:
- direct reduction of unscored titles in AniList-driven combinations, especially `('anilist',)` and `('anilist','mal')`

## Root Cause Summary
Unscored titles are primarily data sparsity at source level, not aggregation math bugs.

Dominant contributors:
- AniList null ratings (largest absolute contributor)
- Kitsu null ratings (highest null ratio)
- MAL still has partial nulls in lower-engagement tails

## Execution Plan (Next Run)
1. Re-fetch sources (full):
   - `scraper/fetch_anilist.py`
   - `scraper/fetch_mal.py`
   - `scraper/fetch_kitsu.py`
   - `scraper/fetch_mangadex.py`
2. Rebuild pipeline:
   - `pipeline/clean.py`
   - `pipeline/deduplicate.py`
   - `pipeline/aggregate.py`
3. Re-profile unscored metrics using the profiling script.
4. Compare against baseline:
   - delta of total unscored
   - delta by source combo
   - null-rate shift per source

## Success Criteria
- `unscored_titles` drops below baseline `11348`
- meaningful decrease in AniList-dominant combos
- no regression in build/runtime for backend/frontend

## Risks / Notes
- Kitsu may remain sparse due upstream API data quality
- MAL improvements require full (not test) fetch runs to show full effect
- dedup mapping quality can affect whether a title receives at least one non-null rating source

## Future Optional Improvements
1. Add a post-fetch quality report per source:
   - non-null rating coverage %, count distributions
2. Add a minimal confidence floor rule (optional product decision):
   - keep score null if confidence too low, even when one weak rating exists
3. Add weekly drift monitoring for null-rate changes by source
