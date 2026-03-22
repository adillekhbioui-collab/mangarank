# ManhwaRank — Genre Relationship Map

> **Skills to invoke:** `@frontend-design` `@interaction-design`
> **File:** `genre_relationship_map.md`
> **Project:** ManhwaRank — Manhwa & Manhua Discovery App
> **Stack:** React · D3.js · Motion · FastAPI · Supabase · PostgreSQL

---

## Project Context

ManhwaRank aggregates manhwa and manhua data from four sources: AniList, MAL,
MangaDex, and Kitsu. The database contains ~24,000 deduplicated manga in the
`manga_rankings` table. Each record has a `genres` column of type `text[]`
containing all genre tags unified from all sources.

The app has a **Charts tab** dedicated to authoritative editorial data
visualizations. It currently shows ranked lists (Top 100, Most Popular, etc.).

The current genre filter requires users to know genre names in advance —
a discoverability problem for new users.

### Design System (must be respected)

```css
:root {
  /* DARK MODE */
  --bg-primary:     #0D0B0E;
  --bg-secondary:   #141118;
  --bg-elevated:    #1C1822;
  --accent-red:     #C1121F;
  --accent-gold:    #C9A84C;
  --accent-muted:   #6B4E71;
  --text-primary:   #F0EBF4;
  --text-secondary: #9B8FA8;
  --text-ghost:     #3D3545;
  --border:         #2A2330;
}

[data-theme="light"] {
  /* LIGHT MODE */
  --bg-primary:     #F5F0EB;
  --bg-secondary:   #EDE8E1;
  --bg-elevated:    #E4DED5;
  --accent-red:     #C1121F;
  --accent-gold:    #A07C20;
  --text-primary:   #1A1410;
  --text-secondary: #5C5248;
  --text-ghost:     #B8AFA6;
  --border:         #D4CEC7;
}
```

**Fonts:** Playfair Display (headings) · DM Mono (data/labels) · Inter (body)

**Philosophy:** Editorial authority. Every element reinforces that ManhwaRank
is the definitive ranking source — not a casual content catalog.

---

## Feature Overview — Genre Universe

A data visualization that maps the **co-occurrence relationships** between
genres across the entire manga database. Answers the question:

> *"When a manga has genre X, which other genres does it most often also have?"*

This insight is only possible because ManhwaRank aggregates data from four
sources. No single-site app can produce this cross-source genre landscape.

### Two Views

| View | Description | Best For |
|---|---|---|
| **Network** (default) | Force-directed bubble graph | Visual discovery, exploration |
| **Heatmap** | Genre × Genre correlation grid | Data analysis, comparisons |

Both views read from the same API endpoint.

---

## Part 1 — Dependencies

Install before building:

```bash
npm install d3 motion
```

| Library | Used For |
|---|---|
| `d3` | Force simulation, SVG rendering, D3 transitions |
| `motion` | Spring physics: bubble selection + panel slide only |

**Rule:** Motion handles spring-based animations only (2 use cases).
D3 handles all graph element transitions.
CSS handles all panel, UI, and entrance animations.

---

## Part 2 — Backend

### Database Queries

No new data collection needed. Everything comes from `manga_rankings`.

**Co-occurrence query:**

```sql
SELECT
  a.genre AS genre_a,
  b.genre AS genre_b,
  COUNT(*) AS co_occurrence
FROM
  manga_rankings,
  unnest(genres) AS a(genre),
  unnest(genres) AS b(genre)
WHERE
  a.genre < b.genre
  AND array_length(genres, 1) > 1
  AND aggregated_score IS NOT NULL
GROUP BY a.genre, b.genre
ORDER BY co_occurrence DESC
LIMIT 200;
```

**Per-genre totals (for bubble sizing):**

```sql
SELECT
  unnest(genres) AS genre,
  COUNT(*) AS manga_count,
  ROUND(AVG(aggregated_score)::numeric, 2) AS avg_score
FROM manga_rankings
WHERE aggregated_score IS NOT NULL
GROUP BY genre
ORDER BY manga_count DESC;
```

### New FastAPI Endpoint

```
GET /genres/relationships
```

**Response structure:**

```json
{
  "nodes": [
    { "genre": "Action", "manga_count": 8421, "avg_score": 76.3 }
  ],
  "edges": [
    { "genre_a": "Action", "genre_b": "Adventure",
      "co_occurrence": 4821, "strength": 0.94 }
  ],
  "meta": {
    "total_manga": 24466,
    "total_genres": 87,
    "computed_at": "2026-03-20T10:00:00Z"
  }
}
```

**Strength:** `strength = co_occurrence / max_co_occurrence_in_dataset`

**Filters:**
- Only edges where `co_occurrence >= 10`
- Maximum 300 edges (top by co_occurrence)
- All nodes that appear in at least one edge

**24-hour memory cache:**

```python
from datetime import datetime, timedelta

_cache = {"data": None, "expires": None}

def get_relationships_cached():
    now = datetime.utcnow()
    if _cache["data"] is None or now > _cache["expires"]:
        _cache["data"] = compute_relationships()
        _cache["expires"] = now + timedelta(hours=24)
    return _cache["data"]

@app.get("/genres/relationships")
def genres_relationships():
    return get_relationships_cached()
```

---

## Part 3 — Network View (D3.js Force Graph)

Create `src/components/charts/GenreNetwork.jsx`

### Visual Specifications

**Nodes:**

| Property | Value |
|---|---|
| Size | `radius = 8 + (manga_count / max_count) * 32` |
| Fill default | `--bg-elevated` |
| Fill selected | `--accent-red` at 30% opacity |
| Fill dimmed | `--bg-secondary` at 20% opacity |
| Border default | 1px `--border` |
| Border selected | 2px `--accent-red` |
| Label | DM Mono uppercase 9px `--text-secondary` below bubble |
| Label selected | DM Mono uppercase 9px `--accent-red` |

**Edges:**

| Property | Value |
|---|---|
| Stroke default | `--border` at 40% opacity |
| Stroke highlighted | `--accent-red` at 40% opacity |
| Stroke dimmed | `--border` at 5% opacity |
| Width | `1 + strength * 4` (1px–5px) |

**Force simulation:**

```javascript
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(edges)
    .id(d => d.genre)
    .strength(d => d.strength * 0.3)
    .distance(d => 120 - d.strength * 60))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collision", d3.forceCollide().radius(d => d.radius + 15));
```

**Natural clusters that should emerge:**
- Action / Adventure / Fantasy / Martial Arts
- Romance / Drama / Comedy / Slice of Life
- Horror / Thriller / Psychological / Mystery

### Interactions

**Click a node:**
1. Spring bounce to 1.3× (Motion — see Part 5)
2. Connected nodes gently pulse to 1.1×
3. Unconnected nodes fade to 15% opacity (D3 transition 250ms)
4. Unconnected edges fade to 5% opacity (D3 transition 250ms)
5. Detail panel springs in from right (Motion — see Part 5)

**Click empty space:** Deselect everything. Panel springs out.

**Hover an edge:** Tooltip appears:
```
ACTION + ADVENTURE
4,821 manga share both genres   [Browse both →]
```
DM Mono 11px · `--bg-elevated` background · 1px `--border` · no radius.

**Zoom/pan:** D3 zoom. `+` `−` buttons top-right. `Reset view` link.
Min 0.5× · Max 3×.

### Detail Panel

Width 280px · `--bg-secondary` background · 1px `--border` left edge.
Springs in/out with Motion AnimatePresence (see Part 5).

```
[GENRE NAME — Playfair Display bold 24px --accent-red]

MANGA COUNT          AVERAGE SCORE
[count] titles       [score] / 100

TOP RELATED GENRES
  [genre] ──────────── [count] shared  (× 5)

TOP 3 MANGA IN THIS GENRE
  [compact strip card × 3]
  (cover + title + score, 64px height)

[Browse all [genre] manga →]
```

"Browse all" navigates to `/?genre_include=[genre]`
reusing the existing URL state filter system.

---

## Part 4 — Heatmap View

Create `src/components/charts/GenreHeatmap.jsx`

Show **top 30 genres by manga_count** only. Full grid is unreadable.

### Color Scale

```javascript
const isDark = !document.documentElement.hasAttribute('data-theme');

const colorScale = d3.scaleSequential()
  .domain([0, maxCoOccurrence])
  .interpolator(d3.interpolate(
    isDark ? '#1C1822' : '#E4DED5',   // --bg-elevated per theme
    '#C1121F'                          // --accent-red always same
  ));
```

**Cell hover:** scale(1.05) + red shadow · Tooltip with count
**Cell click:** Navigate to `/?genre_include=A&genre_include=B`
**Diagonal cells:** Solid `--accent-red` = total manga count for that genre
**Axis labels:** DM Mono uppercase 9px · columns rotated 45°

---

## Part 5 — Animation Specifications

> **Skill instruction:** Apply the `@frontend-design` skill animation guidelines.
> Focus on two high-impact moments only:
> 1. Initial graph load sequence
> 2. Genre selection interaction
>
> All other transitions: 150–250ms ease, subtle.
> Never animate layout shifts or pagination.

---

### Initial Load Sequence

**Phase 1 — Container entrance (0–200ms):**

```css
.genre-network-container {
  animation: networkFadeIn 200ms ease forwards;
}
@keyframes networkFadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
```

Section heading with Motion:

```javascript
<motion.h2
  initial={{ opacity: 0, y: 12 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.2, ease: "easeOut" }}
>
  GENRE UNIVERSE
</motion.h2>
```

**Phase 2 — Bubbles emerge (200ms–2200ms):**

Let the D3 simulation run visually on first load.
Bubbles start collapsed at center and expand as they spread:

```javascript
// Nodes enter with expanding radius
nodeEnter.append("circle")
  .attr("r", 0)
  .transition().duration(400)
  .delay((d, i) => i * 8)
  .attr("r", d => d.radius);

// Edges draw in with stroke-dashoffset
linkEnter
  .attr("stroke-dasharray", function() { return this.getTotalLength(); })
  .attr("stroke-dashoffset", function() { return this.getTotalLength(); })
  .transition().duration(600).delay(400)
  .attr("stroke-dashoffset", 0);
```

**Phase 3 — Ready signal (2200ms):**

```javascript
<motion.p
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ delay: 2.2, duration: 0.4 }}
>
  Click any genre to explore its relationships
</motion.p>
```

**On subsequent renders** (tab revisit) — skip animation entirely:

```javascript
if (hasRenderedBefore) {
  simulation.stop();
  for (let i = 0; i < 300; i++) simulation.tick();
  renderStaticGraph(nodes, edges);   // instant, no animation
} else {
  renderAnimatedGraph(nodes, edges); // full entrance sequence
  setHasRenderedBefore(true);
}
```

---

### Node Selection — Spring Physics (Motion)

```javascript
import { animate } from 'motion';

// Selected bubble — elastic spring bounce
animate(selectedNodeElement, { scale: 1.3 }, {
  type: "spring", stiffness: 400, damping: 25
});

// Connected nodes — gentler spring
connectedNodes.forEach(el => {
  animate(el, { scale: 1.1 }, {
    type: "spring", stiffness: 200, damping: 20
  });
});

// Unconnected nodes — D3 transition (no spring needed)
d3.selectAll(".node.unconnected")
  .transition().duration(250)
  .attr("opacity", 0.15);

// Unconnected edges — D3 transition
d3.selectAll(".edge.unconnected")
  .transition().duration(250)
  .attr("opacity", 0.05);
```

---

### Detail Panel — Spring Slide (Motion)

```javascript
import { AnimatePresence, motion } from 'motion/react';

<AnimatePresence>
  {selectedGenre && (
    <motion.div
      className="detail-panel"
      initial={{ x: 280, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 280, opacity: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
    >
      <motion.div
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: 0.05 } }
        }}
        initial="hidden"
        animate="visible"
      >
        {[genreName, statsRow, ...relatedGenres, ...topManga].map((item, i) => (
          <motion.div
            key={i}
            variants={{
              hidden:   { opacity: 0, y: 8 },
              visible:  { opacity: 1, y: 0,
                transition: { duration: 0.2, ease: "easeOut" } }
            }}
          >
            {item}
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  )}
</AnimatePresence>
```

---

### Heatmap Entrance — CSS Wave

```css
.heatmap-row {
  opacity: 0;
  transform: translateY(8px);
  animation: rowReveal 0.3s ease forwards;
}

/* Generate delays for rows 1-30 */
/* nth-child(n) delay: calc((n - 1) * 20ms) */

@keyframes rowReveal {
  to { opacity: 1; transform: translateY(0); }
}

.heatmap-cell {
  transition: transform 120ms ease, box-shadow 120ms ease;
  cursor: pointer;
}

.heatmap-cell:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(193, 18, 31, 0.2);
  z-index: 10;
  position: relative;
}
```

---

### View Toggle — CSS Directional Crossfade

```css
.view-enter {
  animation: slideInRight 180ms ease forwards;
}

.view-exit {
  animation: slideOutLeft 180ms ease forwards;
  position: absolute;
  top: 0; left: 0; width: 100%;
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes slideOutLeft {
  from { opacity: 1; transform: translateX(0); }
  to   { opacity: 0; transform: translateX(-20px); }
}
```

---

### Reduced Motion (Required)

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

In JavaScript:

```javascript
const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)'
).matches;

if (prefersReducedMotion) {
  // Skip all entrance animation — render instantly
  simulation.stop();
  for (let i = 0; i < 300; i++) simulation.tick();
  renderStaticGraph(nodes, edges);
}
```

---

### Animation Performance Rules

| Rule | Reason |
|---|---|
| Animate `transform` and `opacity` only | GPU-accelerated, no layout recalculation |
| D3 transitions on SVG DOM directly | No React re-renders during animation |
| Motion only for 2 spring animations | Minimum overhead |
| Pre-compute on revisit | No re-animation on tab switch |
| CSS nth-child for stagger | No JS loop needed |

---

## Part 6 — Charts Tab Integration

### Section Header on Charts Page

```
GENRE UNIVERSE
─────────────────────────────────────────────────────────
How 87 genres relate across 24,466 manhwa & manhua.
Aggregated from AniList · MAL · MangaDex · Kitsu

[○ Network]  [○ Heatmap]                   [↗ Fullscreen]
```

### Fullscreen Mode

```javascript
<AnimatePresence>
  {isFullscreen && (
    <motion.div
      className="fullscreen-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
    >
      <button onClick={() => setFullscreen(false)}>✕ CLOSE</button>
      <GenreNetwork fullscreen />
    </motion.div>
  )}
</AnimatePresence>
```

Background: `--bg-primary`. The network fills the entire screen.

### Loading State

```jsx
<div className="network-skeleton">
  {Array.from({ length: 20 }).map((_, i) => (
    <div key={i} className="skeleton-bubble" style={{
      width:  `${20 + Math.random() * 60}px`,
      height: `${20 + Math.random() * 60}px`,
      left:   `${Math.random() * 80}%`,
      top:    `${Math.random() * 80}%`,
      animationDelay: `${i * 0.1}s`
    }} />
  ))}
  <p className="loading-text">Computing genre relationships...</p>
</div>
```

```css
.skeleton-bubble {
  position: absolute;
  border-radius: 50%;
  background: var(--bg-elevated);
  animation: shimmer 1.5s ease-in-out infinite alternate;
}
.loading-text {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  color: var(--text-ghost);
  text-align: center;
  position: absolute;
  bottom: 24px;
  width: 100%;
}
```

### Error State

DM Mono 11px `--text-secondary` with a `Retry` button.
Never crashes the Charts page.

---

## Part 7 — Mobile Behavior

On screens below 768px:

1. Hide the Network view tab entirely
2. Show Heatmap only, limited to top 15 genres
3. Heatmap scrolls horizontally inside a fixed container
4. Detail panel becomes a **draggable bottom sheet:**

```javascript
<motion.div
  className="bottom-sheet"
  initial={{ y: "100%" }}
  animate={{ y: 0 }}
  exit={{ y: "100%" }}
  transition={{ type: "spring", stiffness: 300, damping: 30 }}
  drag="y"
  dragConstraints={{ top: 0 }}
  onDragEnd={(e, info) => {
    if (info.offset.y > 100) setSelectedGenre(null);
  }}
>
  {panelContent}
</motion.div>
```

Pulling the sheet downward more than 100px dismisses it.

---

## Verification Checklist

### Backend
- [ ] `GET /genres/relationships` returns correct nodes and edges
- [ ] Co-occurrence counts match manual SQL results
- [ ] 24-hour cache prevents repeated SQL queries
- [ ] Cached response returns within 500ms

### Network Graph — Animation
- [ ] Bubbles animate from center outward on first load only
- [ ] Edges draw in progressively after bubbles settle
- [ ] Subtitle fades in after 2.2s delay
- [ ] Tab revisit renders instantly with pre-computed positions
- [ ] Selected bubble springs to 1.3× with elastic feel
- [ ] Connected bubbles gently pulse
- [ ] Unconnected nodes fade to 15% with D3 transition
- [ ] Detail panel springs in from right
- [ ] Panel content reveals with 50ms stagger
- [ ] Deselection springs panel out

### Network Graph — Interactions
- [ ] Natural clusters visible (Action/Adventure/Fantasy etc.)
- [ ] Edge hover shows tooltip with co-occurrence count
- [ ] "Browse both" link sets correct genre_include URL params
- [ ] "Browse all [genre]" navigates to filtered browse page
- [ ] Zoom and pan work correctly
- [ ] Reset view returns to centered position

### Heatmap
- [ ] Wave entrance animation plays on load
- [ ] Cell hover scales with red shadow
- [ ] Click navigates with both genres as include filters
- [ ] Diagonal cells show total manga count
- [ ] Color scale correct in both dark and light mode

### Integration
- [ ] View toggle crossfades with directional slide
- [ ] Fullscreen opens/closes with fade
- [ ] Loading state shows skeleton bubbles
- [ ] Error state shows without page crash
- [ ] Both themes correct throughout

### Accessibility
- [ ] `prefers-reduced-motion` skips all animations
- [ ] Only `transform` and `opacity` animated (no layout thrash)
- [ ] D3 transitions never trigger React re-renders
- [ ] Mobile bottom sheet draggable and dismissible

---

## What Must Not Change

| Element | Reason |
|---|---|
| Existing Charts ranked lists | This section adds to, not replaces |
| URL state filter system | Browse links reuse existing params |
| Design tokens and typography | Brand consistency |
| `GET /genres` endpoint | Still used by filter sidebar |
| All existing filter functionality | No regression |
| `--accent-red: #C1121F` | Same in both themes |

---

## Expected Data Insights

```
Strongest (thick lines / deep red in heatmap):
  Action    ↔  Adventure     ~4,800 shared manga
  Action    ↔  Fantasy       ~3,100 shared manga
  Romance   ↔  Drama         ~2,800 shared manga
  Fantasy   ↔  Adventure     ~2,200 shared manga

Weakest (near-invisible):
  Horror         ↔  Romance        very few
  Comedy         ↔  Psychological  very few
  Slice of Life  ↔  Martial Arts   very few
```

The natural emergence of genre clusters without manual configuration
is the visual proof that multi-source aggregation produces genuine
insights no single-site app could generate.
