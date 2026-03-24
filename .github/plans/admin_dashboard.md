# ManhwaRank — Admin Data Quality Dashboard

> **Skill:** `@frontend-design`
> **File:** `admin_dashboard.md`
> **Project:** ManhwaRank — Manhwa & Manhua Discovery App
> **Stack:** React · FastAPI · Supabase · Recharts

---

## Project Context

ManhwaRank aggregates manhwa and manhua data from four sources: AniList, MAL,
MangaDex, and Kitsu. The pipeline runs manually and produces a `manga_rankings`
table consumed by the public frontend. The owner currently monitors data quality
by running SQL queries manually in Supabase.

**The problem this dashboard solves:**
The owner needs to check pipeline health, unscored manga counts, and source
coverage regularly — but has no visual interface to do so. All monitoring
happens via raw SQL. This dashboard replaces that with an instant visual
overview accessible at `/admin`.

---

## Scope — Phase 1 (Admin Only)

This is a **private admin dashboard**, not a user-facing page.

It is protected by a simple password stored in an environment variable.
No auth library, no user accounts — just a single password gate.

A **Phase 2 user-facing dashboard** will be built later once a login system
and event logging infrastructure are added. This document covers Phase 1 only.

---

## Design Direction

> **Skill instruction:** Apply the `@frontend-design` skill.
> Design direction: **CONTROL ROOM**
> Think mission control, Bloomberg terminal, a ship's navigation dashboard.
> Dense with information but organized with military precision.
> The one unforgettable thing: every metric has a health status color that
> tells you at a glance if something needs attention — green, amber, or red.
> No decorative elements. Pure data authority.

### Design Tokens (inherit from main app)

```css
/* Same CSS variables as the rest of ManhwaRank */
--bg-primary:     #0D0B0E;
--bg-secondary:   #141118;
--bg-elevated:    #1C1822;
--accent-red:     #C1121F;
--accent-gold:    #C9A84C;
--text-primary:   #F0EBF4;
--text-secondary: #9B8FA8;
--text-ghost:     #3D3545;
--border:         #2A2330;

/* Dashboard-specific status colors */
--status-good:    #2D6A4F;   /* dark green  */
--status-warn:    #B5850A;   /* amber       */
--status-bad:     #C1121F;   /* accent-red  */
--status-good-fg: #74C69D;   /* light green text */
--status-warn-fg: #F4C430;   /* yellow text */
--status-bad-fg:  #FF6B6B;   /* light red text  */
```

**Fonts:** DM Mono throughout — this is a data terminal, not an editorial page.
Playfair Display is NOT used on the admin dashboard.

---

## Part 1 — Access Protection

### Password Gate Component

```
Route: /admin
If not authenticated → show password gate
If authenticated → show dashboard
Auth stored in sessionStorage (clears when tab closes — intentional)
```

```jsx
// src/pages/AdminPage.jsx

import { useState } from 'react';
import AdminDashboard from '../components/admin/AdminDashboard';

const ADMIN_PASSWORD = process.env.REACT_APP_ADMIN_PASSWORD || 'manhwarank-admin';

export default function AdminPage() {
  const [authed, setAuthed] = useState(
    () => sessionStorage.getItem('admin-auth') === 'true'
  );
  const [input,  setInput]  = useState('');
  const [error,  setError]  = useState(false);

  const handleSubmit = () => {
    if (input === ADMIN_PASSWORD) {
      sessionStorage.setItem('admin-auth', 'true');
      setAuthed(true);
    } else {
      setError(true);
      setTimeout(() => setError(false), 1500);
    }
  };

  if (authed) return <AdminDashboard />;

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-primary)',
    }}>
      <div style={{
        width: 320,
        border: '1px solid var(--border)',
        padding: '32px',
        background: 'var(--bg-secondary)',
      }}>
        <div style={{
          fontFamily: '"DM Mono"', fontSize: '10px',
          letterSpacing: '0.2em', textTransform: 'uppercase',
          color: 'var(--text-ghost)', marginBottom: '20px',
        }}>
          Admin Access
        </div>
        <input
          type="password"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          placeholder="Enter password"
          style={{
            width: '100%', padding: '10px 0',
            background: 'none',
            border: 'none', borderBottom: `1px solid ${error ? 'var(--status-bad)' : 'var(--border)'}`,
            color: 'var(--text-primary)',
            fontFamily: '"DM Mono"', fontSize: '13px',
            outline: 'none', marginBottom: '20px',
            transition: 'border-color 150ms ease',
          }}
        />
        {error && (
          <div style={{
            fontFamily: '"DM Mono"', fontSize: '10px',
            color: 'var(--status-bad-fg)', marginBottom: '12px',
            letterSpacing: '0.1em',
          }}>
            INCORRECT PASSWORD
          </div>
        )}
        <button onClick={handleSubmit} style={{
          width: '100%', padding: '10px',
          background: 'var(--accent-red)', border: 'none',
          color: 'white', fontFamily: '"DM Mono"',
          fontSize: '10px', letterSpacing: '0.15em',
          textTransform: 'uppercase', cursor: 'pointer',
        }}>
          Enter
        </button>
      </div>
    </div>
  );
}
```

Add to `.env`:
```
REACT_APP_ADMIN_PASSWORD=your-secret-password-here
```

Add route to your React Router config:
```jsx
<Route path="/admin" element={<AdminPage />} />
```

---

## Part 2 — Backend Endpoints

Add these four endpoints to `backend/main.py`.
All query existing tables — no new data collection needed.

### Endpoint 1 — Pipeline Health Overview

```
GET /admin/stats
```

```python
@app.get("/admin/stats")
def admin_stats():
    # Total manga in rankings
    total = supabase.table("manga_rankings").select("id", count="exact").execute()

    # Unscored manga
    unscored = supabase.table("manga_rankings") \
        .select("id", count="exact") \
        .is_("aggregated_score", "null") \
        .execute()

    # Total raw records
    raw_total = supabase.table("manga_raw").select("id", count="exact").execute()

    # Last updated timestamp
    last_updated = supabase.table("manga_rankings") \
        .select("updated_at") \
        .order("updated_at", desc=True) \
        .limit(1) \
        .execute()

    total_count   = total.count or 0
    unscored_count = unscored.count or 0
    scored_count  = total_count - unscored_count
    score_rate    = round((scored_count / total_count * 100), 1) if total_count else 0

    return {
        "total_manga":      total_count,
        "scored_manga":     scored_count,
        "unscored_manga":   unscored_count,
        "score_rate_pct":   score_rate,
        "total_raw_records": raw_total.count or 0,
        "last_updated":     last_updated.data[0]["updated_at"] if last_updated.data else None,
    }
```

### Endpoint 2 — Per-Source Null Rate Breakdown

```
GET /admin/source-health
```

```python
@app.get("/admin/source-health")
def admin_source_health():
    sources = ["anilist", "mal", "mangadex", "kitsu"]
    result = []

    for source in sources:
        total = supabase.table("manga_raw") \
            .select("id", count="exact") \
            .eq("source_site", source) \
            .execute()

        null_rating = supabase.table("manga_raw") \
            .select("id", count="exact") \
            .eq("source_site", source) \
            .is_("rating", "null") \
            .execute()

        null_views = supabase.table("manga_raw") \
            .select("id", count="exact") \
            .eq("source_site", source) \
            .is_("view_count", "null") \
            .execute()

        t = total.count or 0
        nr = null_rating.count or 0
        nv = null_views.count or 0

        result.append({
            "source":            source,
            "total_records":     t,
            "null_rating_count": nr,
            "null_rating_pct":   round(nr / t * 100, 1) if t else 0,
            "null_views_count":  nv,
            "null_views_pct":    round(nv / t * 100, 1) if t else 0,
        })

    return result
```

### Endpoint 3 — Score Distribution

```
GET /admin/score-distribution
```

```python
@app.get("/admin/score-distribution")
def admin_score_distribution():
    # Group scores into buckets of 10
    data = supabase.table("manga_rankings") \
        .select("aggregated_score") \
        .not_.is_("aggregated_score", "null") \
        .execute()

    buckets = {f"{i}-{i+10}": 0 for i in range(0, 100, 10)}

    for row in data.data:
        score = row["aggregated_score"]
        bucket_start = (int(score) // 10) * 10
        key = f"{bucket_start}-{bucket_start+10}"
        if key in buckets:
            buckets[key] += 1

    return [{"range": k, "count": v} for k, v in buckets.items()]
```

### Endpoint 4 — Source Coverage Breakdown

```
GET /admin/coverage
```

```python
@app.get("/admin/coverage")
def admin_coverage():
    # Count manga by how many sources they appear in
    # Uses manga_raw grouped by title
    data = supabase.table("manga_raw") \
        .select("title, source_site") \
        .execute()

    from collections import defaultdict
    title_sources = defaultdict(set)
    for row in data.data:
        title_sources[row["title"]].add(row["source_site"])

    distribution = defaultdict(int)
    for sources in title_sources.values():
        distribution[len(sources)] += 1

    return [
        {"sources": k, "manga_count": v}
        for k, v in sorted(distribution.items())
    ]
```

---

## Part 3 — Dashboard Layout

Create `src/components/admin/AdminDashboard.jsx`

### Page Structure

```
/admin
│
├── Header bar
│     MANHWARANK · ADMIN  [Last updated: 2 days ago]  [Refresh]  [← Back to site]
│
├── Row 1 — KPI Cards (4 cards)
│     Total Manga | Scored Manga | Unscored Manga | Score Rate %
│
├── Row 2 — Two columns
│     Left (60%): Source Health Table
│     Right (40%): Score Distribution Bar Chart
│
├── Row 3 — Source Coverage
│     Horizontal bar showing manga with 1/2/3/4 sources
│
└── Row 4 — Quick Actions
      [Run Enrichment Docs] [View Raw SQL] [Supabase Dashboard →]
```

---

### KPI Cards Component

Each card has a **health status** computed from thresholds:

| Metric | Green | Amber | Red |
|---|---|---|---|
| Score Rate % | >= 80% | 60–79% | < 60% |
| Unscored Count | < 5,000 | 5,000–9,000 | > 9,000 |
| Days since last update | <= 3 | 4–7 | > 7 |
| Total manga | >= 20,000 | 15,000–19,999 | < 15,000 |

```jsx
function KPICard({ label, value, unit, status, sublabel }) {
  const statusColors = {
    good: { bg: 'rgba(45,106,79,0.15)', border: 'var(--status-good)',
            text: 'var(--status-good-fg)' },
    warn: { bg: 'rgba(181,133,10,0.15)', border: 'var(--status-warn)',
            text: 'var(--status-warn-fg)' },
    bad:  { bg: 'rgba(193,18,31,0.15)',  border: 'var(--status-bad)',
            text: 'var(--status-bad-fg)' },
  };
  const c = statusColors[status] || statusColors.good;

  return (
    <div style={{
      background: c.bg,
      border: `1px solid ${c.border}`,
      padding: '20px 18px',
      flex: 1,
    }}>
      <div style={{
        fontFamily: '"DM Mono"', fontSize: '8px',
        letterSpacing: '0.2em', textTransform: 'uppercase',
        color: 'var(--text-ghost)', marginBottom: '10px',
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: '"DM Mono"', fontSize: '28px',
        fontWeight: 700, color: c.text, lineHeight: 1,
      }}>
        {value}
        {unit && (
          <span style={{ fontSize: '14px', marginLeft: '4px',
                         color: 'var(--text-secondary)' }}>
            {unit}
          </span>
        )}
      </div>
      {sublabel && (
        <div style={{
          fontFamily: '"DM Mono"', fontSize: '9px',
          color: 'var(--text-ghost)', marginTop: '6px',
        }}>
          {sublabel}
        </div>
      )}
    </div>
  );
}
```

Usage:
```jsx
<div style={{ display: 'flex', gap: '1px', marginBottom: '1px' }}>
  <KPICard
    label="Total Manga"
    value={stats.total_manga.toLocaleString()}
    status={stats.total_manga >= 20000 ? 'good' : stats.total_manga >= 15000 ? 'warn' : 'bad'}
    sublabel="in manga_rankings"
  />
  <KPICard
    label="Scored Manga"
    value={stats.scored_manga.toLocaleString()}
    status={stats.score_rate_pct >= 80 ? 'good' : stats.score_rate_pct >= 60 ? 'warn' : 'bad'}
  />
  <KPICard
    label="Unscored Manga"
    value={stats.unscored_manga.toLocaleString()}
    status={stats.unscored_manga < 5000 ? 'good' : stats.unscored_manga < 9000 ? 'warn' : 'bad'}
    sublabel="missing all source ratings"
  />
  <KPICard
    label="Score Coverage"
    value={stats.score_rate_pct}
    unit="%"
    status={stats.score_rate_pct >= 80 ? 'good' : stats.score_rate_pct >= 60 ? 'warn' : 'bad'}
  />
</div>
```

---

### Source Health Table Component

```jsx
function SourceHealthTable({ sources }) {
  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
      <div style={{
        padding: '14px 18px',
        borderBottom: '1px solid var(--border)',
        fontFamily: '"DM Mono"', fontSize: '9px',
        letterSpacing: '0.2em', textTransform: 'uppercase',
        color: 'var(--text-ghost)',
      }}>
        Source Health
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {['Source', 'Records', 'Null Rating %', 'Null Views %', 'Status'].map(h => (
              <th key={h} style={{
                padding: '10px 18px', textAlign: 'left',
                fontFamily: '"DM Mono"', fontSize: '8px',
                letterSpacing: '0.15em', textTransform: 'uppercase',
                color: 'var(--text-ghost)',
                borderBottom: '1px solid var(--border)',
              }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sources.map(s => {
            const health = s.null_rating_pct < 40 ? 'good'
                         : s.null_rating_pct < 70 ? 'warn' : 'bad';
            const statusText = { good: 'HEALTHY', warn: 'PARTIAL', bad: 'SPARSE' };
            const statusColor = {
              good: 'var(--status-good-fg)',
              warn: 'var(--status-warn-fg)',
              bad:  'var(--status-bad-fg)',
            };

            return (
              <tr key={s.source} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '12px 18px', fontFamily: '"DM Mono"',
                             fontSize: '11px', color: 'var(--text-primary)',
                             textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  {s.source}
                </td>
                <td style={{ padding: '12px 18px', fontFamily: '"DM Mono"',
                             fontSize: '11px', color: 'var(--text-secondary)' }}>
                  {s.total_records.toLocaleString()}
                </td>
                <td style={{ padding: '12px 18px' }}>
                  <NullRateBar pct={s.null_rating_pct} />
                </td>
                <td style={{ padding: '12px 18px' }}>
                  <NullRateBar pct={s.null_views_pct} />
                </td>
                <td style={{ padding: '12px 18px', fontFamily: '"DM Mono"',
                             fontSize: '9px', letterSpacing: '0.15em',
                             color: statusColor[health] }}>
                  {statusText[health]}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function NullRateBar({ pct }) {
  const color = pct < 40 ? 'var(--status-good-fg)'
               : pct < 70 ? 'var(--status-warn-fg)'
               : 'var(--status-bad-fg)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--border)', borderRadius: 2 }}>
        <div style={{ width: `${pct}%`, height: '100%',
                      background: color, borderRadius: 2,
                      transition: 'width 600ms ease' }} />
      </div>
      <span style={{ fontFamily: '"DM Mono"', fontSize: '10px',
                     color, minWidth: 36, textAlign: 'right' }}>
        {pct}%
      </span>
    </div>
  );
}
```

---

### Score Distribution Chart

Use Recharts — already available in your stack:

```jsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function ScoreDistributionChart({ data }) {
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border)',
      padding: '14px 18px',
    }}>
      <div style={{
        fontFamily: '"DM Mono"', fontSize: '9px',
        letterSpacing: '0.2em', textTransform: 'uppercase',
        color: 'var(--text-ghost)', marginBottom: '16px',
      }}>
        Score Distribution
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} barCategoryGap="20%">
          <XAxis
            dataKey="range"
            tick={{ fontFamily: '"DM Mono"', fontSize: 8,
                   fill: 'var(--text-ghost)', letterSpacing: 1 }}
            axisLine={{ stroke: 'var(--border)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontFamily: '"DM Mono"', fontSize: 8,
                   fill: 'var(--text-ghost)' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              fontFamily: '"DM Mono"', fontSize: 10,
              color: 'var(--text-primary)',
            }}
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
          />
          <Bar dataKey="count" fill="var(--accent-red)" radius={[2,2,0,0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

### Source Coverage Bar

Shows how many manga are backed by 1, 2, 3, or 4 sources:

```jsx
function SourceCoverageBar({ data }) {
  const total = data.reduce((s, d) => s + d.manga_count, 0);
  const colors = ['var(--status-bad-fg)', 'var(--status-warn-fg)',
                  'var(--status-good-fg)', 'var(--accent-gold)'];
  const labels = ['1 source', '2 sources', '3 sources', '4 sources'];

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border)',
      padding: '20px 18px',
    }}>
      <div style={{
        fontFamily: '"DM Mono"', fontSize: '9px',
        letterSpacing: '0.2em', textTransform: 'uppercase',
        color: 'var(--text-ghost)', marginBottom: '16px',
      }}>
        Source Coverage — how many sources back each manga's score
      </div>

      {/* Stacked bar */}
      <div style={{ display: 'flex', height: 24, borderRadius: 2,
                    overflow: 'hidden', marginBottom: 16 }}>
        {data.map((d, i) => (
          <div
            key={d.sources}
            title={`${labels[i]}: ${d.manga_count.toLocaleString()} manga`}
            style={{
              width: `${(d.manga_count / total) * 100}%`,
              background: colors[i] || 'var(--text-ghost)',
              transition: 'width 600ms ease',
            }}
          />
        ))}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        {data.map((d, i) => (
          <div key={d.sources} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8,
                          background: colors[i] || 'var(--text-ghost)',
                          borderRadius: 1 }} />
            <span style={{ fontFamily: '"DM Mono"', fontSize: '9px',
                           color: 'var(--text-secondary)' }}>
              {labels[i] || `${d.sources} sources`}:&nbsp;
              <strong style={{ color: 'var(--text-primary)' }}>
                {d.manga_count.toLocaleString()}
              </strong>
              &nbsp;<span style={{ color: 'var(--text-ghost)' }}>
                ({Math.round(d.manga_count / total * 100)}%)
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### Quick Actions Row

```jsx
function QuickActions() {
  const actions = [
    {
      label: 'Enrichment Docs',
      desc: 'How to run targeted rating enrichment',
      href: 'https://github.com/YOUR_USERNAME/manhwarank/blob/main/UNSCORED_MANGA_PLAN.md',
    },
    {
      label: 'Supabase Dashboard',
      desc: 'Direct database access',
      href: 'https://supabase.com/dashboard',
    },
    {
      label: 'Render Logs',
      desc: 'Backend deployment logs',
      href: 'https://dashboard.render.com',
    },
  ];

  return (
    <div style={{
      display: 'flex', gap: '1px',
      borderTop: '1px solid var(--border)', paddingTop: '1px',
    }}>
      {actions.map(a => (
        <a
          key={a.label}
          href={a.href}
          target="_blank"
          rel="noreferrer"
          style={{
            flex: 1, padding: '16px 18px',
            background: 'var(--bg-secondary)',
            border: 'none', textDecoration: 'none',
            borderLeft: '3px solid var(--border)',
            transition: 'border-color 150ms ease',
            display: 'block',
          }}
          onMouseEnter={e => e.currentTarget.style.borderLeftColor = 'var(--accent-red)'}
          onMouseLeave={e => e.currentTarget.style.borderLeftColor = 'var(--border)'}
        >
          <div style={{ fontFamily: '"DM Mono"', fontSize: '10px',
                        letterSpacing: '0.15em', textTransform: 'uppercase',
                        color: 'var(--text-primary)', marginBottom: '4px' }}>
            {a.label} →
          </div>
          <div style={{ fontFamily: '"DM Mono"', fontSize: '9px',
                        color: 'var(--text-ghost)' }}>
            {a.desc}
          </div>
        </a>
      ))}
    </div>
  );
}
```

---

### Full AdminDashboard Component

```jsx
// src/components/admin/AdminDashboard.jsx

import { useState, useEffect } from 'react';
import { motion } from 'motion/react';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function AdminDashboard() {
  const [stats,        setStats]        = useState(null);
  const [sourceHealth, setSourceHealth] = useState(null);
  const [scoreDist,    setScoreDist]    = useState(null);
  const [coverage,     setCoverage]     = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [lastFetch,    setLastFetch]    = useState(null);

  const fetchAll = async () => {
    setLoading(true);
    const [s, sh, sd, cv] = await Promise.all([
      fetch(`${BASE_URL}/admin/stats`).then(r => r.json()),
      fetch(`${BASE_URL}/admin/source-health`).then(r => r.json()),
      fetch(`${BASE_URL}/admin/score-distribution`).then(r => r.json()),
      fetch(`${BASE_URL}/admin/coverage`).then(r => r.json()),
    ]);
    setStats(s);
    setSourceHealth(sh);
    setScoreDist(sd);
    setCoverage(cv);
    setLastFetch(new Date());
    setLoading(false);
  };

  useEffect(() => { fetchAll(); }, []);

  // Compute days since last pipeline run
  const daysSinceUpdate = stats?.last_updated
    ? Math.floor((Date.now() - new Date(stats.last_updated)) / 86400000)
    : null;

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      fontFamily: '"DM Mono", monospace',
    }}>

      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px', height: 52,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-secondary)',
        position: 'sticky', top: 0, zIndex: 50,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ fontSize: '13px', fontWeight: 700,
                         color: 'var(--text-primary)', letterSpacing: '0.1em' }}>
            MANHWA<span style={{ color: 'var(--accent-red)' }}>RANK</span>
          </span>
          <span style={{ fontSize: '8px', color: 'var(--text-ghost)',
                         letterSpacing: '0.2em', textTransform: 'uppercase',
                         borderLeft: '1px solid var(--border)', paddingLeft: 12 }}>
            Admin
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {lastFetch && (
            <span style={{ fontSize: '9px', color: 'var(--text-ghost)',
                           letterSpacing: '0.1em' }}>
              Fetched {lastFetch.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchAll}
            disabled={loading}
            style={{
              fontFamily: '"DM Mono"', fontSize: '9px',
              letterSpacing: '0.15em', textTransform: 'uppercase',
              color: loading ? 'var(--text-ghost)' : 'var(--accent-red)',
              background: 'none', border: '1px solid currentColor',
              padding: '5px 12px', cursor: loading ? 'default' : 'pointer',
            }}
          >
            {loading ? 'Loading...' : '↺ Refresh'}
          </button>
          <a href="/" style={{
            fontFamily: '"DM Mono"', fontSize: '9px',
            letterSpacing: '0.15em', textTransform: 'uppercase',
            color: 'var(--text-ghost)', textDecoration: 'none',
          }}>
            ← Back to site
          </a>
        </div>
      </div>

      {/* Content */}
      {loading && !stats ? (
        <div style={{ padding: 48, textAlign: 'center',
                      color: 'var(--text-ghost)', fontSize: '10px',
                      letterSpacing: '0.2em' }}>
          LOADING DASHBOARD DATA...
        </div>
      ) : (
        <div style={{ padding: '1px', display: 'flex', flexDirection: 'column', gap: '1px' }}>

          {/* Row 1: KPI Cards */}
          {stats && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              style={{ display: 'flex', gap: '1px' }}
            >
              <KPICard
                label="Total Manga"
                value={stats.total_manga.toLocaleString()}
                status={stats.total_manga >= 20000 ? 'good' : stats.total_manga >= 15000 ? 'warn' : 'bad'}
                sublabel="in manga_rankings"
              />
              <KPICard
                label="Scored Manga"
                value={stats.scored_manga.toLocaleString()}
                status={stats.score_rate_pct >= 80 ? 'good' : stats.score_rate_pct >= 60 ? 'warn' : 'bad'}
                sublabel={`${stats.score_rate_pct}% coverage`}
              />
              <KPICard
                label="Unscored Manga"
                value={stats.unscored_manga.toLocaleString()}
                status={stats.unscored_manga < 5000 ? 'good' : stats.unscored_manga < 9000 ? 'warn' : 'bad'}
                sublabel="missing all source ratings"
              />
              <KPICard
                label="Last Pipeline Run"
                value={daysSinceUpdate === 0 ? 'Today' : `${daysSinceUpdate}d ago`}
                status={daysSinceUpdate <= 3 ? 'good' : daysSinceUpdate <= 7 ? 'warn' : 'bad'}
                sublabel="days since aggregate.py ran"
              />
            </motion.div>
          )}

          {/* Row 2: Source Health + Score Distribution */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: 0.08 }}
            style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: '1px' }}
          >
            {sourceHealth && <SourceHealthTable sources={sourceHealth} />}
            {scoreDist && <ScoreDistributionChart data={scoreDist} />}
          </motion.div>

          {/* Row 3: Coverage */}
          {coverage && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: 0.14 }}
            >
              <SourceCoverageBar data={coverage} />
            </motion.div>
          )}

          {/* Row 4: Quick Actions */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2, delay: 0.2 }}
          >
            <QuickActions />
          </motion.div>

        </div>
      )}
    </div>
  );
}
```

---

## Part 4 — What Triggers Status Colors

The dashboard auto-colors every metric based on thresholds.
When you open it you see at a glance if anything needs attention.

| Metric | 🟢 Green | 🟡 Amber | 🔴 Red |
|---|---|---|---|
| Score coverage % | ≥ 80% | 60–79% | < 60% |
| Unscored count | < 5,000 | 5,000–9,000 | > 9,000 |
| Days since update | ≤ 3 days | 4–7 days | > 7 days |
| Total manga | ≥ 20,000 | 15,000–19,999 | < 15,000 |
| Source null rating % | < 40% | 40–70% | > 70% |

---

## Part 5 — Phase 2 Placeholder

Add this section at the bottom of the dashboard as a visual reminder
of what will be added when user accounts and logging are implemented:

```jsx
function Phase2Placeholder() {
  const planned = [
    'Daily active users',
    'Most searched titles',
    'Most clicked manga',
    'Popular filter combinations',
    'User retention rate',
    'Watchlist additions per day',
  ];

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px dashed var(--border)',
      padding: '20px 18px',
      margin: '1px 0',
    }}>
      <div style={{
        fontFamily: '"DM Mono"', fontSize: '9px',
        letterSpacing: '0.2em', textTransform: 'uppercase',
        color: 'var(--text-ghost)', marginBottom: '12px',
      }}>
        Phase 2 — User Analytics (requires login system + event logging)
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {planned.map(item => (
          <div key={item} style={{
            fontFamily: '"DM Mono"', fontSize: '9px',
            color: 'var(--text-ghost)',
            border: '1px dashed var(--border)',
            padding: '4px 10px',
            opacity: 0.5,
          }}>
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Verification Checklist

- [ ] `/admin` route added to React Router
- [ ] Password gate works — wrong password shows error
- [ ] Correct password stores session and shows dashboard
- [ ] Closing tab clears auth (sessionStorage)
- [ ] All 4 backend endpoints return data without errors
- [ ] KPI cards show correct values from `/admin/stats`
- [ ] Status colors are correct (green/amber/red) for each metric
- [ ] Source health table shows all 4 sources with null rates
- [ ] NullRateBar widths match the percentages
- [ ] Score distribution chart renders bars correctly
- [ ] Source coverage stacked bar adds up to 100%
- [ ] Refresh button re-fetches all 4 endpoints
- [ ] "Back to site" link returns to main app
- [ ] Quick action links open in new tab
- [ ] Phase 2 placeholder section visible at bottom
- [ ] Dashboard respects dark/light theme tokens
- [ ] Mobile layout is readable (columns stack vertically below 768px)

---

## What Must Not Change

| Element | Reason |
|---|---|
| All public-facing pages | Admin is a completely separate route |
| Existing API endpoints | New `/admin/*` endpoints are additive only |
| Design tokens | Admin reuses the same CSS variables |
| Database schema | All queries use existing tables |
