# ManhwaRank — Phase 2: User Analytics & Event Logging

> **File:** `phase2_analytics.md`
> **Project:** ManhwaRank — Manhwa & Manhua Discovery App
> **Prerequisite:** Phase 1 admin dashboard fully deployed and stable
> **Stack:** React · FastAPI · Supabase · Umami · Python

---

## Overview

Phase 1 gave you a data quality dashboard — a tool for you as the owner
to monitor pipeline health. Phase 2 adds a completely different layer:
**understanding how users actually use the site.**

The six metrics planned in Phase 1's placeholder section:

| Metric | Source |
|---|---|
| Daily active users | Umami (automatic) |
| Most searched titles | Umami custom event |
| Most clicked manga | Umami custom event |
| Popular filter combinations | Supabase events table |
| User retention cohorts | Umami (automatic) |
| Watchlist additions per day | Supabase events table |

---

## Architecture Decision: Two-Layer Approach

Phase 2 uses **two complementary tools** rather than one:

### Layer 1 — Umami (passive tracking)
Handles everything that does not require custom data:
- Page views, unique visitors, daily/weekly/monthly active users
- Referral sources, device types, screen sizes
- Session duration and bounce rate
- Geographic distribution
- Automatic retention cohort analysis

**Why Umami over Google Analytics:**
- Open source and self-hostable (free on Render)
- Privacy-friendly — no cookies, GDPR compliant by default
- No ads, no data selling, no third-party tracking
- Clean minimal dashboard that is actually pleasant to use
- One script tag in `index.html` and it works

### Layer 2 — Supabase events table (custom tracking)
Handles events that need your manga-specific data:
- Which manga titles were searched
- Which filter combinations were used
- Which manga detail pages were opened
- Watchlist additions and removals
- Genre relationship map interactions

---

## Part 1 — Umami Setup

### Deploy Umami on Render (free)

Umami requires a PostgreSQL database. You already have Supabase — but
Umami works best with its own dedicated database. Render provides a free
PostgreSQL instance.

**Step 1 — Create a free Render PostgreSQL database:**
1. Go to render.com → New → PostgreSQL
2. Name: `manhwarank-umami-db`
3. Free tier → Create Database
4. Copy the **Internal Database URL**

**Step 2 — Deploy Umami as a Render Web Service:**
1. Go to render.com → New → Web Service
2. Connect repository: `https://github.com/umami-software/umami`
   (fork it first or use directly)
3. Configure:
```
Name:           manhwarank-umami
Runtime:        Node
Build Command:  yarn install && yarn build
Start Command:  yarn start
```
4. Environment variables:
```
DATABASE_URL    = {Internal Database URL from step 1}
HASH_SALT       = {any random string, e.g. "manhwarank-salt-2026"}
```
5. Deploy. Access at `https://manhwarank-umami.onrender.com`
6. Default login: `admin` / `umami` — **change this immediately**

**Step 3 — Add your site to Umami:**
1. Log into Umami dashboard
2. Settings → Websites → Add Website
3. Name: ManhwaRank, Domain: your Vercel URL
4. Copy the tracking script

**Step 4 — Add tracking script to React app:**

In `public/index.html` add inside `<head>`:
```html
<script
  async
  defer
  src="https://manhwarank-umami.onrender.com/script.js"
  data-website-id="YOUR_WEBSITE_ID_FROM_UMAMI"
></script>
```

That is it. Umami now automatically tracks page views, sessions,
referrers, and device types with zero additional code.

---

## Part 2 — Custom Event Tracking in React

For manga-specific events, use Umami's custom event API alongside
the Supabase events table for events that need to be queryable.

### Umami Custom Events (lightweight, no backend needed)

Add a `useAnalytics` hook:

```javascript
// src/hooks/useAnalytics.js

export function useAnalytics() {
  const track = (eventName, eventData = {}) => {
    // Umami custom event
    if (window.umami) {
      window.umami.track(eventName, eventData);
    }
  };

  return { track };
}
```

### Events to Track — Where and How

#### Search Events
In your search input component, fire on search submission (not on
every keystroke — only when the user commits to a search):

```javascript
const { track } = useAnalytics();

// On search submit (Enter key or search button click)
const handleSearch = (query) => {
  if (query.trim().length > 0) {
    track('search', { query: query.trim().toLowerCase() });
  }
  // ... rest of search logic
};
```

#### Manga Click Events
In your manga strip card component, fire when a user navigates
to a detail page:

```javascript
const handleMangaClick = (manga) => {
  track('manga_click', {
    title:  manga.title,
    score:  manga.aggregated_score,
    rank:   manga.rank,
  });
  // ... navigate to detail page
};
```

#### Filter Usage Events
In your filter sidebar, fire when a filter is committed (not on
every slider drag — only when the user releases):

```javascript
// Fire when genre is added to include/exclude
const handleGenreAdd = (genre, type) => {
  track('filter_genre', { genre, type }); // type: 'include' or 'exclude'
};

// Fire when status filter changes
const handleStatusChange = (status) => {
  track('filter_status', { status });
};

// Fire when sort changes
const handleSortChange = (sortBy) => {
  track('filter_sort', { sort_by: sortBy });
};
```

#### Category Tab Events
In your category navigation:

```javascript
const handleCategoryClick = (category) => {
  track('category_view', { category });
};
```

#### Genre Universe Interactions
In GenreNetwork.jsx, when a genre node is selected:

```javascript
const handleNodeClick = (genre) => {
  track('genre_network_click', { genre: genre.genre });
};
```

---

## Part 3 — Supabase Events Table

For events that need to be queryable with your manga data (watchlist
adds, filter combinations), write directly to Supabase. Umami does not
give you SQL access to correlate events with your manga_rankings data.

### Schema

Run in Supabase SQL editor:

```sql
CREATE TABLE events (
  id           bigserial PRIMARY KEY,
  event_type   text NOT NULL,
  session_id   text,
  manga_title  text,
  genre        text,
  filter_state jsonb,
  metadata     jsonb,
  created_at   timestamptz DEFAULT now()
);

-- Index for common queries
CREATE INDEX idx_events_type       ON events (event_type);
CREATE INDEX idx_events_created_at ON events (created_at DESC);
CREATE INDEX idx_events_manga      ON events (manga_title)
  WHERE manga_title IS NOT NULL;

-- Row Level Security: allow anonymous inserts, no reads from client
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_anon_insert" ON events
  FOR INSERT TO anon
  WITH CHECK (true);

-- Only service role can read (your backend)
CREATE POLICY "allow_service_read" ON events
  FOR SELECT TO service_role
  USING (true);
```

### Session ID Generation

Users have no accounts, so generate an anonymous session ID stored
in sessionStorage. It resets when the tab closes — intentional:

```javascript
// src/utils/session.js

export function getSessionId() {
  let id = sessionStorage.getItem('session-id');
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem('session-id', id);
  }
  return id;
}
```

### Events to Write to Supabase

Only write to Supabase for events you need to query with SQL later.
Not every event needs to be in Supabase — Umami handles the rest.

```javascript
// src/utils/logEvent.js

import { createClient } from '@supabase/supabase-js';
import { getSessionId } from './session';

const supabase = createClient(
  process.env.REACT_APP_SUPABASE_URL,
  process.env.REACT_APP_SUPABASE_ANON_KEY
);

export async function logEvent(eventType, data = {}) {
  try {
    await supabase.from('events').insert({
      event_type:  eventType,
      session_id:  getSessionId(),
      manga_title: data.manga_title || null,
      genre:       data.genre       || null,
      filter_state: data.filter_state || null,
      metadata:    data.metadata    || null,
    });
  } catch {
    // Never crash the app for an analytics failure
    // Silently swallow all errors
  }
}
```

**Events that go to Supabase:**

```javascript
// Watchlist add/remove — most important for Phase 2 dashboard
logEvent('watchlist_add', {
  manga_title: manga.title,
  metadata: { category: 'reading' }
});

logEvent('watchlist_remove', {
  manga_title: manga.title,
  metadata: { from_category: 'dropped' }
});

// Complex filter combinations — hard to capture in Umami
logEvent('filter_applied', {
  filter_state: {
    genre_include: activeGenreIncludes,
    genre_exclude: activeGenreExcludes,
    status:        activeStatus,
    sort_by:       activeSortBy,
    min_chapters:  activeMinChapters,
  }
});

// Manga detail page views — to correlate with manga data
logEvent('manga_view', {
  manga_title: manga.title,
  metadata: {
    score:  manga.aggregated_score,
    status: manga.status,
  }
});
```

---

## Part 4 — New Backend Endpoints for Phase 2

Add these to `backend/main.py` alongside the existing `/admin/*` endpoints.
All read from the new `events` table.

### Endpoint 1 — Top Searched Titles

```
GET /admin/analytics/searches
```

```python
@app.get("/admin/analytics/searches")
def analytics_searches(days: int = 30, limit: int = 20):
    """Most searched titles in the last N days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    data = supabase.table("events") \
        .select("metadata") \
        .eq("event_type", "search") \
        .gte("created_at", cutoff) \
        .execute()

    from collections import Counter
    queries = Counter()
    for row in data.data:
        q = (row.get("metadata") or {}).get("query")
        if q:
            queries[q] += 1

    return [
        {"query": q, "count": c}
        for q, c in queries.most_common(limit)
    ]
```

### Endpoint 2 — Most Viewed Manga

```
GET /admin/analytics/manga-views
```

```python
@app.get("/admin/analytics/manga-views")
def analytics_manga_views(days: int = 30, limit: int = 20):
    """Most visited manga detail pages in the last N days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    data = supabase.table("events") \
        .select("manga_title") \
        .eq("event_type", "manga_view") \
        .gte("created_at", cutoff) \
        .not_.is_("manga_title", "null") \
        .execute()

    from collections import Counter
    counts = Counter(row["manga_title"] for row in data.data)

    return [
        {"title": t, "views": c}
        for t, c in counts.most_common(limit)
    ]
```

### Endpoint 3 — Popular Filter Combinations

```
GET /admin/analytics/filters
```

```python
@app.get("/admin/analytics/filters")
def analytics_filters(days: int = 30, limit: int = 15):
    """Most used filter combinations."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    data = supabase.table("events") \
        .select("filter_state") \
        .eq("event_type", "filter_applied") \
        .gte("created_at", cutoff) \
        .not_.is_("filter_state", "null") \
        .execute()

    from collections import Counter
    combos = Counter()
    for row in data.data:
        fs = row.get("filter_state") or {}
        # Build a readable summary of the filter state
        parts = []
        if fs.get("genre_include"):
            parts.append(f"include:{','.join(fs['genre_include'][:2])}")
        if fs.get("status") and fs["status"] != "all":
            parts.append(f"status:{fs['status']}")
        if fs.get("sort_by") and fs["sort_by"] != "score":
            parts.append(f"sort:{fs['sort_by']}")
        if parts:
            combos[" + ".join(parts)] += 1

    return [
        {"combination": k, "count": v}
        for k, v in combos.most_common(limit)
    ]
```

### Endpoint 4 — Watchlist Activity

```
GET /admin/analytics/watchlist
```

```python
@app.get("/admin/analytics/watchlist")
def analytics_watchlist(days: int = 30):
    """Watchlist additions per day for the last N days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    data = supabase.table("events") \
        .select("created_at, event_type, manga_title") \
        .in_("event_type", ["watchlist_add", "watchlist_remove"]) \
        .gte("created_at", cutoff) \
        .order("created_at") \
        .execute()

    from collections import defaultdict
    daily = defaultdict(lambda: {"adds": 0, "removes": 0})

    for row in data.data:
        day = row["created_at"][:10]  # YYYY-MM-DD
        if row["event_type"] == "watchlist_add":
            daily[day]["adds"] += 1
        else:
            daily[day]["removes"] += 1

    # Most added manga
    add_events = [r for r in data.data if r["event_type"] == "watchlist_add"]
    from collections import Counter
    top_added = Counter(r["manga_title"] for r in add_events if r["manga_title"])

    return {
        "daily":     [{"date": d, **v} for d, v in sorted(daily.items())],
        "top_added": [{"title": t, "count": c} for t, c in top_added.most_common(10)],
    }
```

---

## Part 5 — Phase 2 Dashboard Widgets

These widgets replace the Phase 2 placeholder section in the admin dashboard.
Add them as new rows below the existing Phase 1 content.

### Widget Layout

```
Phase 2 Analytics
─────────────────────────────────────────

Row A: Umami iframe embed (page views, sessions, countries)

Row B: [Top Searches]  [Most Viewed Manga]
        (bar chart)     (ranked list)

Row C: [Popular Filters]  [Watchlist Activity]
        (tag cloud)        (area chart)
```

### Umami Embed

Umami provides a shareable URL for each website's analytics.
In Settings → Websites → Share URL, enable public sharing and
copy the share URL. Embed it as an iframe in the dashboard:

```jsx
function UmamiWidget() {
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border)',
      padding: '14px 18px',
    }}>
      <div style={{
        fontFamily: '"DM Mono"', fontSize: '9px',
        letterSpacing: '0.2em', textTransform: 'uppercase',
        color: 'var(--text-ghost)', marginBottom: '12px',
      }}>
        Traffic Overview (powered by Umami)
      </div>
      <iframe
        src="YOUR_UMAMI_SHARE_URL"
        style={{
          width: '100%', height: '400px',
          border: 'none',
          filter: 'invert(1) hue-rotate(180deg)', // makes Umami match dark theme
        }}
      />
    </div>
  );
}
```

The `filter: invert(1) hue-rotate(180deg)` CSS trick inverts Umami's
light theme to roughly match the dark dashboard. Not perfect but good enough.

### Top Searches Widget

```jsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function TopSearchesWidget({ data }) {
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border)',
      padding: '14px 18px',
    }}>
      <WidgetHeader title="Top Searched Titles" period="Last 30 days" />
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" barCategoryGap="15%">
          <XAxis type="number"
            tick={{ fontFamily: '"DM Mono"', fontSize: 8,
                   fill: 'var(--text-ghost)' }}
            axisLine={false} tickLine={false}
          />
          <YAxis type="category" dataKey="query" width={120}
            tick={{ fontFamily: '"DM Mono"', fontSize: 9,
                   fill: 'var(--text-secondary)' }}
            axisLine={false} tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              fontFamily: '"DM Mono"', fontSize: 10,
            }}
          />
          <Bar dataKey="count" fill="var(--accent-red)" radius={[0,2,2,0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### Watchlist Activity Widget

```jsx
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function WatchlistWidget({ data }) {
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border)',
      padding: '14px 18px',
    }}>
      <WidgetHeader title="Watchlist Activity" period="Last 30 days" />
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={data.daily}>
          <XAxis dataKey="date"
            tick={{ fontFamily: '"DM Mono"', fontSize: 8,
                   fill: 'var(--text-ghost)' }}
            axisLine={false} tickLine={false}
            tickFormatter={d => d.slice(5)} // show MM-DD only
          />
          <YAxis
            tick={{ fontFamily: '"DM Mono"', fontSize: 8,
                   fill: 'var(--text-ghost)' }}
            axisLine={false} tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              fontFamily: '"DM Mono"', fontSize: 10,
            }}
          />
          <Area type="monotone" dataKey="adds"
            stroke="var(--status-good-fg)"
            fill="rgba(116,198,157,0.1)"
            strokeWidth={1.5}
          />
          <Area type="monotone" dataKey="removes"
            stroke="var(--status-bad-fg)"
            fill="rgba(255,107,107,0.08)"
            strokeWidth={1.5}
          />
        </AreaChart>
      </ResponsiveContainer>

      {data.top_added?.length > 0 && (
        <>
          <div style={{
            fontFamily: '"DM Mono"', fontSize: '8px',
            letterSpacing: '0.15em', textTransform: 'uppercase',
            color: 'var(--text-ghost)',
            marginTop: '16px', marginBottom: '8px',
          }}>
            Most Added to Watchlist
          </div>
          {data.top_added.slice(0, 5).map((item, i) => (
            <div key={item.title} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              fontFamily: '"DM Mono"', fontSize: '10px',
            }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                {i + 1}. {item.title}
              </span>
              <span style={{ color: 'var(--status-good-fg)' }}>
                +{item.count}
              </span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
```

### Shared Widget Header Component

```jsx
function WidgetHeader({ title, period }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between',
      alignItems: 'baseline', marginBottom: '14px',
    }}>
      <div style={{
        fontFamily: '"DM Mono"', fontSize: '9px',
        letterSpacing: '0.2em', textTransform: 'uppercase',
        color: 'var(--text-ghost)',
      }}>
        {title}
      </div>
      {period && (
        <div style={{
          fontFamily: '"DM Mono"', fontSize: '8px',
          color: 'var(--text-ghost)', opacity: 0.6,
        }}>
          {period}
        </div>
      )}
    </div>
  );
}
```

---

## Part 6 — Privacy Considerations

Since you are collecting user behavior data, be transparent about it.

### What to Add to the Site

A minimal privacy notice in the footer of the main site:

```jsx
function FooterPrivacyNote() {
  return (
    <div style={{
      fontFamily: '"DM Mono"', fontSize: '9px',
      color: 'var(--text-ghost)', textAlign: 'center',
      padding: '12px', letterSpacing: '0.1em',
    }}>
      This site uses privacy-friendly analytics (no cookies, no personal data).
      Watchlist data is stored locally in your browser only.
    </div>
  );
}
```

### What You Do NOT Collect

Make sure these are never sent to Supabase events:
- No IP addresses
- No device fingerprints
- No personally identifiable information
- Session IDs are random UUIDs generated per tab — not linked to any person

---

## Part 7 — Data Retention Policy

The `events` table will grow indefinitely. Add an automatic cleanup:

```sql
-- Run monthly or add as a scheduled function in Supabase
-- Delete events older than 90 days
DELETE FROM events
WHERE created_at < NOW() - INTERVAL '90 days';
```

Or add to your pipeline orchestrator to run after each pipeline cycle:

```python
# In run_enrichment.py or as a separate cleanup script
def cleanup_old_events():
    """Remove events older than 90 days."""
    cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
    supabase.table("events").delete().lt("created_at", cutoff).execute()
    print(f"Cleaned up events older than {cutoff}")
```

---

## Rollout Order

Do these in strict sequence. Do not skip ahead.

```
Step 1: Deploy Umami on Render              (~30 min)
        Verify page views appear in Umami dashboard

Step 2: Add useAnalytics hook to frontend   (~1 hour)
        Add track() calls to search, manga clicks, filters, categories
        Verify events appear in Umami real-time view

Step 3: Create Supabase events table        (~15 min)
        Add logEvent utility
        Add watchlist and filter_applied logging
        Verify rows appear in Supabase table editor

Step 4: Add 4 new backend endpoints         (~1 hour)
        Test each with curl or Postman before connecting to frontend

Step 5: Build Phase 2 dashboard widgets     (~2 hours)
        Replace placeholder section with real widgets
        Verify each widget renders correctly with real data

Step 6: Add privacy footer note             (~10 min)

Step 7: Add events cleanup script           (~15 min)
```

---

## Verification Checklist

### Umami
- [ ] Umami deployed on Render and accessible
- [ ] Default admin password changed
- [ ] ManhwaRank site added to Umami
- [ ] Tracking script in `index.html`
- [ ] Page views appear in Umami within 5 minutes of visiting the site
- [ ] Share URL generated for iframe embed

### Custom Event Tracking
- [ ] `useAnalytics` hook created at `src/hooks/useAnalytics.js`
- [ ] `getSessionId` utility created at `src/utils/session.js`
- [ ] `logEvent` utility created at `src/utils/logEvent.js`
- [ ] Search events fire on query submission (not on keystroke)
- [ ] Manga click events fire on card click
- [ ] Filter events fire on filter change (not during drag)
- [ ] Watchlist add/remove events fire correctly
- [ ] Events visible in Supabase table editor after interactions

### Backend
- [ ] `GET /admin/analytics/searches` returns data
- [ ] `GET /admin/analytics/manga-views` returns data
- [ ] `GET /admin/analytics/filters` returns data
- [ ] `GET /admin/analytics/watchlist` returns daily and top_added

### Dashboard
- [ ] Umami iframe loads in Phase 2 section
- [ ] Top searches bar chart renders correctly
- [ ] Most viewed manga list renders correctly
- [ ] Watchlist area chart shows adds vs removes
- [ ] Top added manga list shows correctly
- [ ] All widgets fail gracefully if endpoint is down

### Privacy
- [ ] Privacy footer note visible on main site
- [ ] No PII in events table (verified by SQL query)
- [ ] Events cleanup script runs without errors

---

## What Must Not Change

| Element | Reason |
|---|---|
| Phase 1 dashboard widgets | Phase 2 adds rows, does not replace |
| All existing API endpoints | New `/admin/analytics/*` are additive |
| `manga_raw` and `manga_rankings` tables | Events table is completely separate |
| User-facing pages | Analytics is passive and invisible to users |
| Watchlist localStorage logic | Supabase events are for counting only, not storage |
