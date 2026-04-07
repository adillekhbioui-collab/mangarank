# Plan 04 Implementation Notes — Sticky Header & Navigation Redesign

Date: 2026-04-07
Status: Completed

## Scope Delivered

1. Mobile-first masthead redesign
- Converted mobile header into a two-row layout:
  - Row 1: prominent brand + auth/theme actions.
  - Row 2: full-width search input.
- Improved mobile touch usability with 44px-safe action controls.

2. Sticky/scroll-aware behavior preserved
- Existing hide-on-scroll/show-on-scroll logic remains active.
- Header still restores when filter sheet opens.

3. Desktop navigation continuity
- Desktop nav tabs remain in-header at `md+`.
- Existing topTab/category behavior preserved.

4. Mobile bottom navigation added
- Added fixed bottom nav for `Browse / Charts / Watchlist` on `<lg`.
- Safe-area padding included for modern mobile devices.
- Active state is visibly highlighted.

5. Mobile content spacing adjustments
- Added mobile bottom padding to content panes to avoid overlap with bottom nav.
- Applied to browse, charts, and watchlist sections.

6. Filter toolbar offset adjusted for mobile header height
- Updated mobile sticky filter toolbar top offset to align under taller mobile masthead.

## Files Updated

- `frontend/src/App.jsx`

## Constraints Verification

- Routing logic unchanged.
- `useSearchParams` filter state logic unchanged.
- Data fetching and backend contracts unchanged.
- Theme toggle and search behavior preserved.

## Validation

- `npm run build` succeeded after final changes.

## Notes

- Bundle-size warning remains an existing project characteristic.
- Legacy CSS remains for untouched surfaces during phased redesign process.
