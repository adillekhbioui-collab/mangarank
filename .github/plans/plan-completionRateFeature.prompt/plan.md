## Plan: Implement Completion Rate Feature (Merged)

This feature introduces a 'Completion Rate' metric sourced from AniList's `statusDistribution` to identify reader retention and group manga into unique categories (Masterpieces, Hard to Finish, Guilty Pleasures).

**Steps**

**Phase 1: Database & Data Pipeline**
1. **Update Database Schema:** Run `ALTER TABLE` commands manually in Supabase SQL editor for `manga_raw` (`count_current`, `count_completed`, `count_dropped`, `count_paused`, `count_planning`) and `manga_rankings` (`completion_rate`, `total_readers`).
2. **Update Scraper (`scraper/fetch_anilist.py`):** Add `statusDistribution` to `GRAPHQL_QUERY`. Extract the 5 counts in `build_record` equivalent. Add these to the upsert payload.
3. **Update Pipeline (`pipeline/aggregate.py`):** Calculate `total_readers = COMPLETED + DROPPED + CURRENT + PAUSED` (exclude `PLANNING`). If total $\ge 1000$, compute `completion_rate`. Add a print breakdown at the end: total valid, total nulls, top 5, and bottom 5 previews.
4. **Data Calibration:** Run a distribution query in Supabase to check `avg_completion`, `bottom_25`, `top_25`, and `avg_score` across `manga_rankings` to validate and tweak thresholds if necessary.

**Phase 2: Backend API Updates (`backend/main.py`)**
5. **Update API Models & Queries:** Add `completion_rate` and `total_readers` to `/manga`, `/manga/{title}`, and `/stats` (average completion, count). Add `sort_by=completion` (nulls last).
6. **New Endpoints using calibrated thresholds:**
   - `GET /top/completion-masterpieces`: `aggregated_score >= 75`, `completion_rate >= 60`, `total_readers >= 1000`, sorted by completion descending.
   - `GET /top/completion-traps`: `aggregated_score >= 75`, `completion_rate < 35`, `total_readers >= 2000`, sorted by score descending. ("Hard to Finish")
   - `GET /top/guilty-pleasures`: `aggregated_score < 70`, `completion_rate >= 65`, `total_readers >= 1000`, sorted by completion descending.

**Phase 3: Frontend Integration**
7. **Detail Page (`frontend/src/MangaDetailPage.jsx`):** Add a visual progress bar (Green for $\ge$ 70%, Yellow for 40-69%, Red for < 40%). Show `{total_readers} AniList readers tracked`. Handle `null` gracefully.
8. **Manga Cards:** Add small indicator badges for extreme completion rates ($\ge$ 70% Green ✓, < 30% Red ⚠).
9. **Navigation & Filters:** Add category tabs for "Masterpieces", "Hard to Finish", and "Guilty Pleasures" with short subtitles. Add a "Reader Behavior" sidebar filter.

**Relevant files**
- `scraper/fetch_anilist.py`
- `pipeline/aggregate.py`
- `backend/main.py`
- `frontend/src/MangaDetailPage.jsx`
- Frontend routing / category components.

**Verification**
1. Run `python fetch_anilist.py` and verify `manga_raw` populates with counts.
2. Run `python aggregate.py` and verify `manga_rankings`, reviewing the printed breakdown.
3. Run the SQL distribution query in Supabase.
4. Test backend endpoints for accurate sorting and stats.
5. Manually verify the UI renders correctly against the new properties.

**Decisions**
- Thresholds strictly follow the 75/35/2000 data-driven rules discussed previously.
- Extensively detailed UI requirements (colors, conditional logic, filtering) added to ensure clear UX.
