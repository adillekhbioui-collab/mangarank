# Personal Watchlist — Implementation Plan

**Feature**: Personal Watchlist  
**Storage**: `localStorage` (no account required)  
**Scope**: Frontend-only feature, zero backend changes  
**Target files**: `frontend/src/` (new files + modifications to existing)

---

## 1. Overview

Allow users to save any manga title to a personal watchlist with four status categories:

| Status | Description |
|---|---|
| `want_to_read` | Queued up for later |
| `reading` | Currently in progress |
| `completed` | Finished reading |
| `dropped` | Abandoned |

All data is persisted in `localStorage` under a single key. No login, no backend calls, no external dependencies.

---

## 2. Data Model

### Storage key
```
manhwarank_watchlist
```

### Shape
```json
{
  "version": 1,
  "entries": {
    "<title>": {
      "title": "Tower of God",
      "cover_url": "https://...",
      "status": "reading",
      "added_at": "2025-03-20T10:00:00Z",
      "updated_at": "2025-03-20T12:30:00Z",
      "notes": ""
    }
  }
}
```

### Key decisions
- Keyed by `title` (URL-safe title string, same as what the backend already uses as its identity key — consistent with the existing upsert-by-title convention).
- `cover_url` and `title` are snapshotted at add-time so the watchlist renders even when offline or if a title is removed from rankings.
- `version: 1` field is included for forward-compatible migrations.

---

## 3. File Structure

```
frontend/src/
├── hooks/
│   └── useWatchlist.js          ← NEW: all localStorage read/write logic
├── components/
│   ├── WatchlistButton.jsx       ← NEW: the per-card status toggle button
│   ├── WatchlistPanel.jsx        ← NEW: full watchlist sidebar/page
│   └── WatchlistStatusBadge.jsx  ← NEW: small inline badge shown on cards
├── pages/
│   └── WatchlistSection.jsx         ← NEW: dedicated /watchlist route
└── App.jsx                       ← MODIFIED: add route + nav entry
```

---

## 4. Hook: `useWatchlist.js`

This is the core of the feature. All components consume this hook.

```js
// frontend/src/hooks/useWatchlist.js

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'manhwarank_watchlist';
const STATUSES = ['want_to_read', 'reading', 'completed', 'dropped'];

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { version: 1, entries: {} };
    const parsed = JSON.parse(raw);
    return parsed?.entries ? parsed : { version: 1, entries: {} };
  } catch {
    return { version: 1, entries: {} };
  }
}

function saveToStorage(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (e) {
    // localStorage quota exceeded — silently fail
    console.warn('Watchlist: storage quota exceeded', e);
  }
}

export function useWatchlist() {
  const [data, setData] = useState(loadFromStorage);

  // Sync across tabs
  useEffect(() => {
    const handler = (e) => {
      if (e.key === STORAGE_KEY) setData(loadFromStorage());
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  const getStatus = useCallback(
    (titleSlug) => data.entries[titleSlug]?.status ?? null,
    [data]
  );

  const addOrUpdate = useCallback((titleSlug, manga, status) => {
    setData((prev) => {
      const now = new Date().toISOString();
      const existing = prev.entries[titleSlug];
      const next = {
        ...prev,
        entries: {
          ...prev.entries,
          [titleSlug]: {
            title: manga.title,
            cover_url: manga.cover_url ?? null,
            status,
            added_at: existing?.added_at ?? now,
            updated_at: now,
            notes: existing?.notes ?? '',
          },
        },
      };
      saveToStorage(next);
      return next;
    });
  }, []);

  const remove = useCallback((titleSlug) => {
    setData((prev) => {
      const entries = { ...prev.entries };
      delete entries[titleSlug];
      const next = { ...prev, entries };
      saveToStorage(next);
      return next;
    });
  }, []);

  const updateNotes = useCallback((titleSlug, notes) => {
    setData((prev) => {
      const entry = prev.entries[titleSlug];
      if (!entry) return prev;
      const next = {
        ...prev,
        entries: {
          ...prev.entries,
          [titleSlug]: { ...entry, notes, updated_at: new Date().toISOString() },
        },
      };
      saveToStorage(next);
      return next;
    });
  }, []);

  // Grouped view for WatchlistSection
  const grouped = STATUSES.reduce((acc, s) => {
    acc[s] = Object.entries(data.entries)
      .filter(([, v]) => v.status === s)
      .sort((a, b) => new Date(b[1].updated_at) - new Date(a[1].updated_at));
    return acc;
  }, {});

  const totalCount = Object.keys(data.entries).length;

  return { getStatus, addOrUpdate, remove, updateNotes, grouped, totalCount, STATUSES };
}
```

### Why this approach
- Single source of truth — one `useState` initialized from storage.
- `storage` event listener keeps multiple open tabs in sync automatically.
- `try/catch` on both read and write — localStorage can be blocked in private browsing modes or when quota is exceeded.

---

## 5. Component: `WatchlistButton.jsx`

Appears on every manga card and on the detail page. Cycles through statuses or removes on second tap of the active status.

```jsx
// frontend/src/components/WatchlistButton.jsx

import { useWatchlist } from '../hooks/useWatchlist';

const STATUS_LABELS = {
  want_to_read: 'Want to read',
  reading:      'Reading',
  completed:    'Completed',
  dropped:      'Dropped',
};

const STATUS_COLORS = {
  want_to_read: 'var(--watchlist-want)',   // blue
  reading:      'var(--watchlist-reading)', // amber
  completed:    'var(--watchlist-done)',    // green
  dropped:      'var(--watchlist-drop)',    // muted red
};

export function WatchlistButton({ manga, titleSlug, compact = false }) {
  const { getStatus, addOrUpdate, remove, STATUSES } = useWatchlist();
  const current = getStatus(titleSlug);

  function handleClick(e) {
    e.stopPropagation(); // don't trigger card navigation
    if (!current) {
      addOrUpdate(titleSlug, manga, 'want_to_read');
    }
    // Dropdown handles status change — see below
  }

  function handleStatusSelect(e, status) {
    e.stopPropagation();
    if (current === status) {
      remove(titleSlug);
    } else {
      addOrUpdate(titleSlug, manga, status);
    }
  }

  if (compact) {
    // Small pill for card overlays
    return (
      <div className="watchlist-compact" onClick={handleClick}>
        {current ? (
          <span style={{ color: STATUS_COLORS[current] }}>
            {STATUS_LABELS[current]}
          </span>
        ) : (
          <span>+ Add</span>
        )}
      </div>
    );
  }

  return (
    <div className="watchlist-btn-group">
      <button
        className={`watchlist-btn ${current ? 'active' : ''}`}
        style={current ? { borderColor: STATUS_COLORS[current], color: STATUS_COLORS[current] } : {}}
        onClick={handleClick}
      >
        {current ? STATUS_LABELS[current] : '+ Add to list'}
      </button>

      {/* Status selector dropdown — shown when already added */}
      {current && (
        <div className="watchlist-dropdown">
          {STATUSES.map((s) => (
            <button
              key={s}
              className={`watchlist-dropdown-item ${s === current ? 'selected' : ''}`}
              onClick={(e) => handleStatusSelect(e, s)}
            >
              {STATUS_LABELS[s]}
              {s === current && <span className="remove-hint">(tap to remove)</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## 6. Component: `WatchlistStatusBadge.jsx`

Tiny inline badge rendered in the top-right corner of manga cards to show watchlist state at a glance.

```jsx
// frontend/src/components/WatchlistStatusBadge.jsx

import { useWatchlist } from '../hooks/useWatchlist';

const BADGE_CONFIG = {
  want_to_read: { label: 'Want',      color: '#3B8BD4' },
  reading:      { label: 'Reading',   color: '#BA7517' },
  completed:    { label: 'Done',      color: '#3B6D11' },
  dropped:      { label: 'Dropped',   color: '#A32D2D' },
};

export function WatchlistStatusBadge({ titleSlug }) {
  const { getStatus } = useWatchlist();
  const status = getStatus(titleSlug);
  if (!status) return null;

  const { label, color } = BADGE_CONFIG[status];
  return (
    <span
      className="watchlist-badge"
      style={{ background: color }}
    >
      {label}
    </span>
  );
}
```

---

## 7. Page: `WatchlistSection.jsx`

Dedicated route at `/watchlist` showing all saved titles grouped by category.

```jsx
// frontend/src/pages/WatchlistSection.jsx

import { useState } from 'react';
import { useWatchlist } from '../hooks/useWatchlist';
import { WatchlistButton } from '../components/WatchlistButton';

const SECTION_META = {
  reading:      { label: 'Currently reading', icon: '▶' },
  want_to_read: { label: 'Want to read',       icon: '⊞' },
  completed:    { label: 'Completed',          icon: '✓' },
  dropped:      { label: 'Dropped',            icon: '×' },
};

export function WatchlistSection() {
  const { grouped, totalCount, remove } = useWatchlist();
  const [activeTab, setActiveTab] = useState('reading');

  if (totalCount === 0) {
    return (
      <div className="watchlist-empty">
        <p>Your watchlist is empty.</p>
        <p>Browse titles and hit <strong>+ Add to list</strong> to save them here.</p>
      </div>
    );
  }

  return (
    <div className="watchlist-page">
      <header className="watchlist-header">
        <h1>My Watchlist</h1>
        <span className="watchlist-total">{totalCount} titles saved</span>
      </header>

      {/* Tab bar */}
      <nav className="watchlist-tabs">
        {Object.entries(SECTION_META).map(([key, meta]) => (
          <button
            key={key}
            className={`watchlist-tab ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
          >
            {meta.icon} {meta.label}
            <span className="watchlist-tab-count">
              {grouped[key].length}
            </span>
          </button>
        ))}
      </nav>

      {/* Active list */}
      <div className="watchlist-grid">
        {grouped[activeTab].length === 0 ? (
          <p className="watchlist-section-empty">Nothing here yet.</p>
        ) : (
          grouped[activeTab].map(([slug, entry]) => (
            <div key={slug} className="watchlist-card">
              {entry.cover_url && (
                <img src={entry.cover_url} alt={entry.title} className="watchlist-card-cover" />
              )}
              <div className="watchlist-card-info">
                <a href={`/manga/${slug}`} className="watchlist-card-title">
                  {entry.title}
                </a>
                <span className="watchlist-card-date">
                  Added {new Date(entry.added_at).toLocaleDateString()}
                </span>
                <WatchlistButton
                  manga={{ title: entry.title, cover_url: entry.cover_url }}
                  titleSlug={slug}
                />
              </div>
            </div>
          ))
        )}
      </div>

      {/* Export / clear actions */}
      <div className="watchlist-actions">
        <button onClick={handleExport} className="watchlist-action-btn">
          Export as JSON
        </button>
        <button onClick={handleClear} className="watchlist-action-btn danger">
          Clear all
        </button>
      </div>
    </div>
  );

  function handleExport() {
    const allEntries = Object.values(SECTION_META)
      .flatMap((_, i) => grouped[Object.keys(SECTION_META)[i]]);
    const blob = new Blob([JSON.stringify(allEntries, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'manhwarank-watchlist.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleClear() {
    if (window.confirm('Clear your entire watchlist? This cannot be undone.')) {
      localStorage.removeItem('manhwarank_watchlist');
      window.location.reload();
    }
  }
}
```

---

## 8. App.jsx Modifications

```jsx
// frontend/src/App.jsx — additions only

// 1. Import new page
import { WatchlistSection } from './pages/WatchlistSection';
import { useWatchlist } from './hooks/useWatchlist';

// 2. Add route (inside your existing <Routes>)
<Route path="/watchlist" element={<WatchlistSection />} />

// 3. Add nav link with live count badge
function WatchlistNavLink() {
  const { totalCount } = useWatchlist();
  return (
    <a href="/watchlist" className="nav-link">
      My List
      {totalCount > 0 && <span className="nav-badge">{totalCount}</span>}
    </a>
  );
}
// Add <WatchlistNavLink /> into your existing nav/header component

// 4. On MangaCard (wherever you render a card):
// Add <WatchlistStatusBadge titleSlug={manga.title} />
// Add <WatchlistButton manga={manga} titleSlug={manga.title} compact />

// 5. On MangaDetailPage:
// Add <WatchlistButton manga={manga} titleSlug={titleSlug} />
// (full size, not compact)
```

---

## 9. CSS Variables to Add

```css
/* frontend/src/index.css or your global stylesheet */

:root {
  --watchlist-want:    #3B8BD4;  /* blue   — want to read */
  --watchlist-reading: #BA7517;  /* amber  — in progress */
  --watchlist-done:    #3B6D11;  /* green  — completed */
  --watchlist-drop:    #A32D2D;  /* red    — dropped */
}
```

These map to the same color ramps already used in the rest of the platform (MangaDex/AniList score colors), keeping visual language consistent.

---

## 10. Implementation Sequence

Execute in this order to keep the app working at every step:

```
Step 1 — Hook only (no UI yet)
  Create frontend/src/hooks/useWatchlist.js
  Verify it reads/writes localStorage correctly in browser console

Step 2 — WatchlistStatusBadge (additive, zero risk)
  Create WatchlistStatusBadge.jsx
  Wire into MangaCard — it renders nothing until a title is added so no visual change yet

Step 3 — WatchlistButton
  Create WatchlistButton.jsx
  Add to MangaCard (compact) and MangaDetailPage (full)
  Test add/change/remove flow end to end

Step 4 — WatchlistSection + Route
  Create WatchlistSection.jsx
  Add /watchlist route to App.jsx
  Test grouped view, tab switching, empty state

Step 5 — Nav badge
  Add WatchlistNavLink to header
  Test count updates reactively as titles are added

Step 6 — Polish
  Add CSS transitions for button state changes
  Verify cross-tab sync (open two windows, add in one, check the other)
  Test private browsing graceful degradation
  Test with 100+ entries for performance
```

---

## 11. Edge Cases and Guardrails

| Scenario | Handling |
|---|---|
| `localStorage` blocked (private mode, some browsers) | `try/catch` on all reads and writes — feature silently degrades, no crash |
| Quota exceeded (rare, ~5MB limit) | `catch` on write with `console.warn`, existing data preserved |
| Title slug changes after being saved | Entry persists but becomes a dead link — acceptable for v1, can add tombstone handling later |
| User clears browser storage externally | App re-initializes to empty state cleanly on next load |
| Multiple tabs open | `window.storage` event listener syncs state across tabs automatically |

---

## 12. What This Feature Does NOT Need

- No backend changes
- No new API endpoints
- No authentication
- No database migrations
- No Supabase reads or writes
- No pipeline changes

This is a **pure frontend feature**. The full implementation can be shipped without touching `scraper/`, `pipeline/`, or `backend/` at all.

---

## 13. Future Extensions (Post-v1)

These are out of scope for the initial implementation but are easy to build on top of this foundation:

1. **Import from JSON** — reverse of the export button, let users restore a backup.
2. **Chapter progress tracking** — store `chapters_read` per entry, show progress bar on cards.
3. **Notes field** — `updateNotes()` is already in the hook, just needs a UI textarea in the watchlist card.
4. **Filter integration** — add a "In my list" toggle to the main browse page to filter the ranked list to only watchlisted titles.
5. **Account sync** — if authentication is ever added, the localStorage data can be migrated to Supabase in a one-time sync without changing the hook's public API.
