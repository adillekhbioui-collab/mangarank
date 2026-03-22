# ManhwaRank — Mobile Optimization Plan

## Overview

This plan addresses the layout and UX issues identified in both mobile screenshots:
- **Screen 1** — Filter/settings panel with misaligned elements
- **Screen 2** — Grid view with clipped card titles and cramped metadata

The goal is a **native-feeling mobile experience** that respects the existing dark aesthetic (black background, red accent `#E5383B`, bold uppercase typography) while adopting proper mobile-first patterns.

---

## Audit: What's Broken

### Header (Both Screens)
| Issue | Cause |
|---|---|
| Logo and search bar are competing for width | Desktop `flex-row` layout not collapsed for mobile |
| "LIGHT" toggle is floating awkwardly below the search | Absolute/relative positioning not adjusted |
| Whole header feels cramped and unbalanced | No `padding` or `safe-area-inset` consideration |

### Filter Panel (Screen 1)
| Issue | Cause |
|---|---|
| GENRES dropdown looks like a desktop `<select>` | Not styled as a mobile-friendly component |
| STATUS options (ALL / ONGOING / COMPLETED) stacked in a plain list | Should be horizontal pill/tab group |
| SORT BY has no visual affordance (just plain text) | Needs a styled dropdown trigger |
| MIN CHAPTERS field looks like raw form input | Needs a thumb-friendly slider or stepper |
| LIST VIEW / GRID VIEW toggle buttons are tiny | Small hit area — below the 44px minimum |
| No visual hierarchy between sections | Sections run together without clear separators |

### Grid View (Screen 2)
| Issue | Cause |
|---|---|
| Card titles are clipped ("Omniscient Read…", "SSS-Class Reviva…") | Grid columns are using fixed widths instead of responsive units |
| "+" ADD button is small and hard to tap | Touch target too small |
| Genre tags overflow and get cut off | No `flex-wrap` or `line-clamp` |
| Rank badge (90, 87...) positioning is acceptable but sizing is inconsistent | Minor |
| Chapter count and views row is dense | Tight spacing on small viewport |

---

## Design Decisions (Mobile-First Principles)

- **Minimum touch target:** 44×44px for all interactive elements
- **Type scale:** Keep uppercase tracking for headings; increase base font to `14px` min on mobile
- **Grid:** True `50% - gap` columns using CSS Grid so cards never clip
- **Filter UX:** Migrate filters to a **bottom sheet** (drawer from bottom) triggered by a sticky toolbar — standard mobile pattern
- **Status toggle:** Replace vertical list with a horizontal **segmented control / pill row**
- **Theme toggle:** Move to the header as an icon-only button, not inline text
- **Safe area:** Add `padding-bottom: env(safe-area-inset-bottom)` for iPhone notch/home bar

---

## Implementation Plan

### Phase 1 — Header Fix

**File target:** Header component (e.g., `Header.tsx` / `Navbar.tsx`)

**Changes:**
```css
/* Mobile header layout */
@media (max-width: 768px) {
  .header {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    /* No wrapping of logo + search */
  }

  .logo {
    flex-shrink: 0;
    font-size: 18px; /* scale down slightly */
  }

  .search-bar {
    width: 100%;
    min-width: 0; /* prevent overflow in grid */
  }

  .theme-toggle {
    /* Convert to icon-only button */
    width: 36px;
    height: 36px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: rgba(255,255,255,0.05);
  }

  .theme-toggle-label {
    display: none; /* hide "LIGHT" text on mobile */
  }
}
```

**Result:** Single clean row — `[LOGO] [SEARCH BAR ————] [☀]`

---

### Phase 2 — Filter Panel → Bottom Sheet

The filter options currently live in the main scroll area. On mobile, this wastes vertical space and creates a jarring layout.

**New pattern:** A sticky bottom toolbar with a **"FILTER"** button that opens a bottom sheet drawer.

**File targets:** Filter components + add `FilterBottomSheet.tsx`

#### 2a — Sticky Filter Toolbar (above grid)

```tsx
// FilterToolbar.tsx
<div className="filter-toolbar">
  <button className="filter-btn" onClick={openSheet}>
    <FilterIcon />
    FILTER
    {activeFilterCount > 0 && <span className="badge">{activeFilterCount}</span>}
  </button>
  <div className="view-toggle">
    <button aria-pressed={view === 'list'} onClick={() => setView('list')}>
      <ListIcon />
    </button>
    <button aria-pressed={view === 'grid'} onClick={() => setView('grid')}>
      <GridIcon />
    </button>
  </div>
  <SortDropdown /> {/* compact inline sort selector */}
</div>
```

```css
.filter-toolbar {
  position: sticky;
  top: 60px; /* below header height */
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #0d0d0d;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 6px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #fff;
  background: transparent;
}

.view-toggle button {
  width: 36px;
  height: 36px; /* ≥44px hit area via padding */
  padding: 4px;
}
```

#### 2b — Bottom Sheet Drawer

```tsx
// FilterBottomSheet.tsx
<AnimatePresence>
  {isOpen && (
    <>
      <motion.div
        className="sheet-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={closeSheet}
      />
      <motion.div
        className="bottom-sheet"
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
        drag="y"
        dragConstraints={{ top: 0 }}
        onDragEnd={(_, info) => {
          if (info.offset.y > 100) closeSheet();
        }}
      >
        <div className="sheet-handle" />
        <div className="sheet-content">
          {/* Filter sections here */}
        </div>
        <button className="apply-btn" onClick={applyAndClose}>
          APPLY FILTERS
        </button>
      </motion.div>
    </>
  )}
</AnimatePresence>
```

```css
.bottom-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: #111;
  border-radius: 16px 16px 0 0;
  max-height: 85vh;
  overflow-y: auto;
  padding-bottom: env(safe-area-inset-bottom, 16px);
}

.sheet-handle {
  width: 36px;
  height: 4px;
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
  margin: 12px auto 20px;
}

.apply-btn {
  position: sticky;
  bottom: 0;
  width: calc(100% - 32px);
  margin: 0 16px;
  height: 48px;
  background: #E5383B;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #fff;
}
```

---

### Phase 3 — Filter Controls Inside the Sheet

#### Genre Selector
Replace the desktop dropdown `<select>` with a **horizontally scrollable chip row**:

```tsx
<div className="filter-section">
  <label className="section-label">GENRES</label>
  <div className="chip-scroll">
    {genres.map(genre => (
      <button
        key={genre}
        className={`chip ${selected.includes(genre) ? 'chip--active' : ''}`}
        onClick={() => toggleGenre(genre)}
      >
        {genre}
      </button>
    ))}
  </div>
</div>
```

```css
.chip-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: none;
}

.chip {
  flex-shrink: 0;
  height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 20px;
  font-size: 12px;
  letter-spacing: 0.05em;
  white-space: nowrap;
  background: transparent;
  color: rgba(255,255,255,0.6);
  transition: all 150ms ease;
}

.chip--active {
  background: #E5383B;
  border-color: #E5383B;
  color: #fff;
}
```

#### Status Toggle → Segmented Control

Replace the stacked text list with a 3-segment pill control:

```tsx
<div className="filter-section">
  <label className="section-label">STATUS</label>
  <div className="segmented-control">
    {['ALL', 'ONGOING', 'COMPLETED'].map(s => (
      <button
        key={s}
        className={`segment ${status === s ? 'segment--active' : ''}`}
        onClick={() => setStatus(s)}
      >
        {s}
      </button>
    ))}
  </div>
</div>
```

```css
.segmented-control {
  display: flex;
  background: rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 3px;
}

.segment {
  flex: 1;
  height: 36px;
  border-radius: 6px;
  font-size: 11px;
  letter-spacing: 0.08em;
  font-weight: 700;
  color: rgba(255,255,255,0.4);
  background: transparent;
  transition: all 200ms ease;
}

.segment--active {
  background: #E5383B;
  color: #fff;
}
```

#### Min Chapters → Range Slider

Replace the plain `0` text input with a styled `<input type="range">`:

```tsx
<div className="filter-section">
  <label className="section-label">
    MIN CHAPTERS <span className="value-badge">{minChapters}</span>
  </label>
  <input
    type="range"
    min={0}
    max={500}
    step={10}
    value={minChapters}
    onChange={e => setMinChapters(Number(e.target.value))}
    className="range-slider"
  />
</div>
```

```css
.range-slider {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
  outline: none;
}

.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #E5383B;
  cursor: pointer;
  box-shadow: 0 0 0 4px rgba(229,56,59,0.2);
}
```

---

### Phase 4 — Grid Card Fix

**File target:** Manga/Manhwa card grid component

#### Fix 1: Proper 2-column grid

```css
.grid-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr); /* NOT fixed px widths */
  gap: 12px;
  padding: 12px 16px;
}
```

#### Fix 2: Card title — clamp to 2 lines

```css
.card-title {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  /* Full width available — no clipping */
}
```

#### Fix 3: Genre tags — wrap properly

```css
.genre-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.genre-tag {
  font-size: 10px;
  letter-spacing: 0.04em;
  color: rgba(255,255,255,0.45);
  /* limit to 3 tags max, hide rest with "+N more" logic */
}
```

#### Fix 4: Metadata row — better spacing

```css
.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.card-meta .divider {
  width: 1px;
  height: 10px;
  background: rgba(255,255,255,0.15);
}
```

#### Fix 5: "+ ADD" button — bigger hit area

```css
.add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  height: 36px; /* min 44px touch area with card padding */
  margin-top: 10px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: rgba(255,255,255,0.6);
  background: transparent;
  transition: all 150ms ease;
}

.add-btn:active {
  background: rgba(229,56,59,0.15);
  border-color: #E5383B;
  color: #E5383B;
}
```

---

### Phase 5 — Category Cards (Masterpieces / Hard to Finish)

These banners are currently a 2-column desktop layout. On narrow screens they should stack or use a horizontal scroll:

```css
@media (max-width: 480px) {
  .category-cards {
    /* Option A: Stack vertically */
    grid-template-columns: 1fr;

    /* Option B: Horizontal scroll */
    /* display: flex; overflow-x: auto; */
  }

  .category-card {
    padding: 20px 16px;
  }

  .category-card h2 {
    font-size: 16px;
  }
}
```

---

### Phase 6 — Polish & Accessibility

| Item | Fix |
|---|---|
| `env(safe-area-inset-*)` | Add to header, bottom sheet, and page bottom padding |
| `font-size: 16px` on all inputs | Prevents iOS auto-zoom on focus |
| `touch-action: manipulation` | Removes 300ms tap delay on buttons |
| `overscroll-behavior: contain` | Prevents body scroll while bottom sheet is open |
| `-webkit-tap-highlight-color: transparent` | Remove grey flash on tap |
| Skeleton loaders | Show animated placeholders while grid loads |

```css
/* Global mobile base fixes */
* {
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}

input, select, textarea {
  font-size: 16px !important; /* prevents iOS zoom */
}

body.sheet-open {
  overflow: hidden;
  overscroll-behavior: contain;
}
```

---

## File Change Checklist

```
[ ] components/Header.tsx          — 3-column grid layout, icon-only theme toggle
[ ] components/FilterPanel.tsx     — Remove from main flow, keep logic only
[ ] components/FilterToolbar.tsx   — NEW: sticky toolbar with filter btn + view toggle
[ ] components/FilterBottomSheet.tsx — NEW: animated drawer with all filter controls
[ ] components/GenreChips.tsx      — NEW: horizontal scroll chip selector
[ ] components/StatusSegment.tsx   — NEW: segmented pill control
[ ] components/ManhwaGrid.tsx      — Fix grid columns, card overflow
[ ] components/ManhwaCard.tsx      — Fix title clamp, tags, ADD button
[ ] components/CategoryBanner.tsx  — Responsive stacking
[ ] styles/globals.css             — Add mobile base fixes (safe area, tap, zoom)
```

---

## Priority Order

1. **P0 — Grid fix** (Phase 4): Cards clipping titles is the most visible UX bug
2. **P0 — Header fix** (Phase 1): Affects every screen
3. **P1 — Filter bottom sheet** (Phases 2–3): Biggest UX improvement
4. **P2 — Polish** (Phase 6): Accessibility & feel
5. **P3 — Category banners** (Phase 5): Lower impact

---

## Testing Checklist

- [ ] Test on 375px (iPhone SE) — smallest common viewport
- [ ] Test on 390px (iPhone 14) — most common
- [ ] Test on 412px (Android large)
- [ ] Verify bottom sheet swipe-to-dismiss works on touch
- [ ] Verify no horizontal scroll on any screen
- [ ] Verify all tap targets ≥ 44px
- [ ] Verify iOS input zoom doesn't trigger
- [ ] Verify safe area padding on iPhone with home bar
