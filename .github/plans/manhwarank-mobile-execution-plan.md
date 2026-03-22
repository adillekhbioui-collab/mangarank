# ManhwaRank Mobile Execution Plan (Codebase-Aligned)

## Goal
Deliver a native-feeling mobile experience without breaking existing URL-driven filter behavior.

## Current Architecture Reality
- Primary UI is in [manhwa-aggregator/frontend/src/App.jsx](manhwa-aggregator/frontend/src/App.jsx)
- Styling is centralized in [manhwa-aggregator/frontend/src/index.css](manhwa-aggregator/frontend/src/index.css)
- Existing filters are URL-backed and must remain shareable/back-forward safe

## Execution Strategy
1. P0: Header + grid readability + touch targets
2. P1: Mobile filter surface (sheet) using existing filter logic
3. P1.5: Mobile-friendly controls inside sheet (segmented status + slider)
4. P2: Mobile navigation affordance for hidden top tabs (Charts/Watchlist)
5. P3: Motion/accessibility polish and device QA

## Work Breakdown

### P0 — Implemented
- Mobile header grid layout and search/toggle spacing
- 2-column mobile grid with improved title/genre/meta readability
- Larger mobile touch targets for key controls
- Body scroll lock class for sheet-open state

### P1 — Implemented
- Sticky mobile toolbar above results
- Filter button with active filter count badge
- Mobile bottom-sheet behavior using existing filter panel
- Backdrop + close/apply interactions

### P1.5 — Implemented
- Segmented status control in mobile filter panel
- Min chapters mobile range slider + value badge
- Desktop status/number controls preserved

### P2 — Next
- Add compact mobile nav chips for `ALL / CHARTS / WATCHLIST`
- Preserve current desktop nav tabs unchanged

### P3 — Next
- Add optional drag-to-dismiss sheet behavior
- Add stronger focus-visible styles and a11y labels on mobile controls
- Validate on 375px / 390px / 412px viewports

## Risks & Guardrails
- Guardrail: do not break URL query param sync
- Guardrail: do not regress desktop layout
- Risk: CSS override conflicts in large stylesheet
- Mitigation: isolate all mobile logic under `@media (max-width: 768px)` and scoped classes

## Validation Checklist
- [x] App compiles: `npm run build --prefix manhwa-aggregator/frontend`
- [ ] 375px viewport: no horizontal overflow
- [ ] 390px viewport: filter sheet open/close feels stable
- [ ] 412px viewport: grid cards do not clip titles
- [ ] Watchlist button remains usable in grid/list on mobile
- [ ] iOS input zoom does not trigger

## Files Changed So Far
- [manhwa-aggregator/frontend/src/App.jsx](manhwa-aggregator/frontend/src/App.jsx)
- [manhwa-aggregator/frontend/src/index.css](manhwa-aggregator/frontend/src/index.css)

## Next Immediate Commit Scope
- P2 mobile nav chips + top-tab switching
- Quick pass for sheet keyboard focus and escape handling
