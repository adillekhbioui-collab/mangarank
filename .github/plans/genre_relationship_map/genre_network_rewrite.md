# ManhwaRank — Genre Network Chart: Complete Rewrite

> **Skills:** `@frontend-design` `@interaction-design`
> **Scope:** Delete and rewrite `src/components/charts/GenreNetwork.jsx` only.
> **Backend, heatmap, and all other files are unchanged.**

---

## Why the Original Failed — Root Cause Diagnosis

The previous implementation had two fatal React + D3 integration bugs:

### Bug 1 — Zero-dimension SVG (causes the collapsed center cluster)
D3's force simulation ran inside `useEffect` and immediately tried to read
the container's `clientWidth` and `clientHeight`. At that point in the React
lifecycle, the DOM element exists but layout has not been calculated yet,
so both dimensions report `0`. The force center becomes `(0, 0)` and every
node collapses on top of each other at the top-left origin.

### Bug 2 — SVG outside viewport (causes the empty black page)
The SVG element had no explicit `width` and `height` attributes. CSS was
expected to size it, but because the parent container also had no defined
height, both collapsed. Nodes rendered correctly but at coordinates that
placed them outside the visible scroll area.

### The Fix
Use a `ResizeObserver` to detect when the container has real pixel dimensions,
then and only then initialize D3. This guarantees the force simulation always
knows the true available space before running a single tick.

---

## What to Delete

Delete the entire existing `src/components/charts/GenreNetwork.jsx` file.
Do not try to patch it — rewrite from scratch using the implementation below.

All other files stay untouched:
- `GenreHeatmap.jsx` — unchanged
- `ChartsPage.jsx` — unchanged (it imports GenreNetwork, which will still work)
- `backend/main.py` — unchanged
- All CSS files — unchanged

---

## Project Context (for agent reference)

**App:** ManhwaRank — manhwa/manhua discovery and ranking app
**Stack:** React, D3 v7, Framer Motion / Motion, FastAPI, Supabase

**API endpoint already exists:**
```
GET /genres/relationships
Returns: { nodes: [...], edges: [...], meta: {...} }
nodes: [{ genre: string, manga_count: number, avg_score: number }]
edges: [{ genre_a: string, genre_b: string, co_occurrence: number, strength: number }]
```

**Design tokens (CSS variables already defined globally):**
```
--bg-primary, --bg-secondary, --bg-elevated
--accent-red: #C1121F
--text-primary, --text-secondary, --text-ghost
--border
Fonts: Playfair Display (headings), DM Mono (labels/data)
```

---

## New Implementation — `GenreNetwork.jsx`

### Architecture Overview

```
GenreNetwork (React)
  │
  ├── useRef(containerRef)      ← measures real DOM dimensions
  ├── useRef(svgRef)            ← D3 attaches here
  ├── useState(dimensions)      ← {width, height} from ResizeObserver
  ├── useState(data)            ← nodes + edges from API
  ├── useState(selectedGenre)   ← currently clicked node
  ├── useState(hoveredEdge)     ← currently hovered edge
  │
  ├── useEffect #1: ResizeObserver
  │     Watches containerRef → updates dimensions state
  │     Only fires when container has real pixel size
  │
  ├── useEffect #2: Data fetch
  │     Calls GET /genres/relationships once on mount
  │     Stores in data state
  │
  ├── useEffect #3: D3 simulation
  │     Depends on [data, dimensions]
  │     ONLY runs when BOTH data is loaded AND dimensions > 0
  │     Cleans up previous simulation on re-run
  │
  └── JSX renders:
        <div ref={containerRef}>       ← measured by ResizeObserver
          <svg ref={svgRef} />         ← D3 draws here
          <DetailPanel />              ← React-rendered, Motion animated
          <Tooltip />                  ← React-rendered
          <Controls />                 ← zoom buttons
        </div>
```

---

## Step-by-Step Implementation

### Step 1 — Component Shell with ResizeObserver

```jsx
import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { AnimatePresence, motion } from 'motion/react';

export default function GenreNetwork() {
  const containerRef = useRef(null);
  const svgRef       = useRef(null);
  const simRef       = useRef(null);   // stores simulation for cleanup

  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [data,       setData]       = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [selected,   setSelected]   = useState(null);
  const [tooltip,    setTooltip]    = useState(null);

  // CRITICAL FIX: Use ResizeObserver to get real dimensions
  // This fires AFTER layout is painted, so dimensions are always real
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions({ width: Math.floor(width), height: Math.floor(height) });
        }
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Data fetch
  useEffect(() => {
    const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    fetch(`${BASE_URL}/genres/relationships`)
      .then(r => r.json())
      .then(json => { setData(json); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  // D3 simulation — only runs when BOTH conditions are true:
  //   1. data is loaded (data !== null)
  //   2. container has real dimensions (width > 0, height > 0)
  useEffect(() => {
    if (!data || dimensions.width === 0 || dimensions.height === 0) return;
    if (!svgRef.current) return;

    renderNetwork(data, dimensions, svgRef, simRef, setSelected, setTooltip);

    // Cleanup: stop simulation when component unmounts or re-renders
    return () => {
      if (simRef.current) {
        simRef.current.stop();
      }
    };
  }, [data, dimensions]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '600px',        // CRITICAL: explicit height — never leave this to CSS alone
        position: 'relative',
        background: 'var(--bg-primary)',
      }}
    >
      {loading && <LoadingState />}
      {error   && <ErrorState error={error} onRetry={() => window.location.reload()} />}
      {!loading && !error && (
        <>
          <svg
            ref={svgRef}
            width={dimensions.width}    // CRITICAL: always explicit width
            height={dimensions.height}  // CRITICAL: always explicit height
            style={{ display: 'block', overflow: 'visible' }}
          />
          <AnimatePresence>
            {selected && (
              <DetailPanel
                genre={selected}
                data={data}
                onClose={() => setSelected(null)}
              />
            )}
          </AnimatePresence>
          {tooltip && <EdgeTooltip tooltip={tooltip} />}
          <ZoomControls svgRef={svgRef} dimensions={dimensions} />
        </>
      )}
    </div>
  );
}
```

---

### Step 2 — The renderNetwork Function

This is the core D3 logic. Extract it outside the component to keep the
component clean. It receives everything it needs as parameters.

```javascript
function renderNetwork(data, dimensions, svgRef, simRef, setSelected, setTooltip) {
  const { width, height } = dimensions;
  const { nodes: rawNodes, edges: rawEdges } = data;

  // ── 1. Prepare data ──────────────────────────────────────────
  const maxCount = Math.max(...rawNodes.map(n => n.manga_count));

  // Deep copy nodes and edges so D3 can mutate them (adds x, y, vx, vy)
  const nodes = rawNodes.map(n => ({
    ...n,
    radius: 8 + (n.manga_count / maxCount) * 32,
    id: n.genre,
  }));

  const edges = rawEdges.map(e => ({
    ...e,
    source: e.genre_a,
    target: e.genre_b,
  }));

  // ── 2. Clear previous SVG content ───────────────────────────
  const svg = d3.select(svgRef.current);
  svg.selectAll('*').remove();

  // ── 3. Set up zoom layer ─────────────────────────────────────
  const zoomLayer = svg.append('g').attr('class', 'zoom-layer');

  const zoom = d3.zoom()
    .scaleExtent([0.4, 3])
    .on('zoom', (event) => {
      zoomLayer.attr('transform', event.transform);
    });

  svg.call(zoom);

  // Store zoom on svg element for ZoomControls to access
  svgRef.current.__zoom = zoom;
  svgRef.current.__zoomBehavior = zoom;

  // ── 4. Draw edges first (behind nodes) ──────────────────────
  const edgeSelection = zoomLayer.append('g').attr('class', 'edges')
    .selectAll('line')
    .data(edges)
    .join('line')
    .attr('class', 'edge')
    .attr('stroke', 'var(--border)')
    .attr('stroke-opacity', 0.4)
    .attr('stroke-width', d => 1 + d.strength * 4)
    .style('cursor', 'pointer')
    .on('mouseenter', (event, d) => {
      setTooltip({
        x: event.clientX,
        y: event.clientY,
        genre_a: d.genre_a,
        genre_b: d.genre_b,
        count: d.co_occurrence,
      });
    })
    .on('mouseleave', () => setTooltip(null));

  // ── 5. Draw node groups ──────────────────────────────────────
  const nodeGroup = zoomLayer.append('g').attr('class', 'nodes')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'node-group')
    .style('cursor', 'pointer');

  // Circle
  nodeGroup.append('circle')
    .attr('r', d => d.radius)
    .attr('fill', 'var(--bg-elevated)')
    .attr('stroke', 'var(--border)')
    .attr('stroke-width', 1);

  // Label
  nodeGroup.append('text')
    .text(d => d.genre.toUpperCase())
    .attr('text-anchor', 'middle')
    .attr('dy', d => d.radius + 14)
    .attr('fill', 'var(--text-secondary)')
    .attr('font-family', '"DM Mono", monospace')
    .attr('font-size', '9px')
    .attr('letter-spacing', '0.1em')
    .style('pointer-events', 'none')
    .style('user-select', 'none');

  // Click handler
  nodeGroup.on('click', (event, d) => {
    event.stopPropagation();

    const connectedGenres = new Set();
    edges.forEach(e => {
      if (e.source.id === d.id || e.source === d.id) connectedGenres.add(e.target.id || e.target);
      if (e.target.id === d.id || e.target === d.id) connectedGenres.add(e.source.id || e.source);
    });

    // Dim unconnected nodes
    nodeGroup.selectAll('circle')
      .transition().duration(250)
      .attr('opacity', n => n.id === d.id || connectedGenres.has(n.id) ? 1 : 0.15);

    // Dim unconnected edges
    edgeSelection
      .transition().duration(250)
      .attr('stroke-opacity', e => {
        const src = e.source.id || e.source;
        const tgt = e.target.id || e.target;
        return (src === d.id || tgt === d.id) ? 0.8 : 0.03;
      })
      .attr('stroke', e => {
        const src = e.source.id || e.source;
        const tgt = e.target.id || e.target;
        return (src === d.id || tgt === d.id) ? 'var(--accent-red)' : 'var(--border)';
      });

    setSelected({
      genre: d.genre,
      manga_count: d.manga_count,
      avg_score: d.avg_score,
      relatedGenres: edges
        .filter(e => {
          const src = e.source.id || e.source;
          const tgt = e.target.id || e.target;
          return src === d.id || tgt === d.id;
        })
        .map(e => {
          const src = e.source.id || e.source;
          const tgt = e.target.id || e.target;
          return {
            genre: src === d.id ? tgt : src,
            count: e.co_occurrence,
          };
        })
        .sort((a, b) => b.count - a.count)
        .slice(0, 5),
    });
  });

  // Click on SVG background to deselect
  svg.on('click', () => {
    nodeGroup.selectAll('circle')
      .transition().duration(250)
      .attr('opacity', 1);

    edgeSelection
      .transition().duration(250)
      .attr('stroke-opacity', 0.4)
      .attr('stroke', 'var(--border)');

    setSelected(null);
  });

  // ── 6. Force simulation ──────────────────────────────────────
  // CRITICAL: forceCenter uses real width/height from ResizeObserver
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges)
      .id(d => d.id)
      .strength(d => d.strength * 0.25)
      .distance(d => 100 - d.strength * 50)
    )
    .force('charge', d3.forceManyBody().strength(-250))
    .force('center', d3.forceCenter(width / 2, height / 2))  // real center
    .force('collision', d3.forceCollide().radius(d => d.radius + 12))
    .force('x', d3.forceX(width / 2).strength(0.05))   // gentle pull to center
    .force('y', d3.forceY(height / 2).strength(0.05)); // prevents drift off-screen

  simRef.current = simulation;

  // Update positions on each tick
  simulation.on('tick', () => {
    // Clamp nodes to stay within SVG bounds
    nodes.forEach(n => {
      n.x = Math.max(n.radius + 10, Math.min(width  - n.radius - 10, n.x));
      n.y = Math.max(n.radius + 10, Math.min(height - n.radius - 10, n.y));
    });

    edgeSelection
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    nodeGroup
      .attr('transform', d => `translate(${d.x}, ${d.y})`);
  });
}
```

---

### Step 3 — Detail Panel Component

```jsx
function DetailPanel({ genre, data, onClose }) {
  return (
    <motion.div
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      style={{
        position:   'absolute',
        top:        0,
        right:      0,
        width:      '280px',
        height:     '100%',
        background: 'var(--bg-secondary)',
        borderLeft: '1px solid var(--border)',
        padding:    '24px 20px',
        overflowY:  'auto',
        zIndex:     10,
      }}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        style={{
          position:   'absolute',
          top:        '16px',
          right:      '16px',
          background: 'none',
          border:     'none',
          color:      'var(--text-ghost)',
          fontFamily: '"DM Mono", monospace',
          fontSize:   '11px',
          cursor:     'pointer',
          letterSpacing: '0.1em',
        }}
      >
        ✕
      </button>

      {/* Genre name */}
      <motion.h3
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        style={{
          fontFamily: '"Playfair Display", serif',
          fontSize:   '22px',
          fontWeight: 700,
          color:      'var(--accent-red)',
          marginBottom: '20px',
          marginTop:    '8px',
          lineHeight: 1.2,
        }}
      >
        {genre.genre}
      </motion.h3>

      {/* Stats row */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          marginBottom: '24px',
        }}
      >
        <div>
          <div style={{ fontFamily: '"DM Mono"', fontSize: '9px',
                        color: 'var(--text-ghost)', letterSpacing: '0.15em',
                        textTransform: 'uppercase', marginBottom: '4px' }}>
            Manga Count
          </div>
          <div style={{ fontFamily: '"DM Mono"', fontSize: '18px',
                        color: 'var(--text-primary)', fontWeight: 700 }}>
            {genre.manga_count.toLocaleString()}
          </div>
        </div>
        <div>
          <div style={{ fontFamily: '"DM Mono"', fontSize: '9px',
                        color: 'var(--text-ghost)', letterSpacing: '0.15em',
                        textTransform: 'uppercase', marginBottom: '4px' }}>
            Avg Score
          </div>
          <div style={{ fontFamily: '"DM Mono"', fontSize: '18px',
                        color: 'var(--accent-red)', fontWeight: 700 }}>
            {genre.avg_score}
          </div>
        </div>
      </motion.div>

      {/* Related genres */}
      {genre.relatedGenres?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <div style={{ fontFamily: '"DM Mono"', fontSize: '9px',
                        color: 'var(--text-ghost)', letterSpacing: '0.15em',
                        textTransform: 'uppercase', marginBottom: '12px' }}>
            Top Related Genres
          </div>
          {genre.relatedGenres.map((rel, i) => {
            const maxCount = genre.relatedGenres[0].count;
            const pct = (rel.count / maxCount) * 100;
            return (
              <motion.div
                key={rel.genre}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.04 }}
                style={{ marginBottom: '10px' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between',
                              alignItems: 'center', marginBottom: '3px' }}>
                  <span style={{ fontFamily: '"DM Mono"', fontSize: '11px',
                                 color: 'var(--text-secondary)',
                                 textTransform: 'uppercase' }}>
                    {rel.genre}
                  </span>
                  <span style={{ fontFamily: '"DM Mono"', fontSize: '10px',
                                 color: 'var(--text-ghost)' }}>
                    {rel.count.toLocaleString()}
                  </span>
                </div>
                <div style={{ height: '2px', background: 'var(--border)',
                              borderRadius: '1px' }}>
                  <div style={{ height: '100%', width: `${pct}%`,
                                background: 'var(--accent-red)',
                                borderRadius: '1px',
                                transition: 'width 400ms ease' }} />
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      )}

      {/* Browse link */}
      <motion.a
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        href={`/?genre_include=${encodeURIComponent(genre.genre)}`}
        style={{
          display:      'block',
          marginTop:    '24px',
          fontFamily:   '"DM Mono", monospace',
          fontSize:     '10px',
          textTransform: 'uppercase',
          letterSpacing: '0.15em',
          color:         'var(--accent-red)',
          textDecoration: 'none',
          borderTop:     '1px solid var(--border)',
          paddingTop:    '16px',
        }}
      >
        Browse all {genre.genre} manga →
      </motion.a>
    </motion.div>
  );
}
```

---

### Step 4 — Edge Tooltip Component

```jsx
function EdgeTooltip({ tooltip }) {
  return (
    <div style={{
      position:   'fixed',
      left:       tooltip.x + 12,
      top:        tooltip.y - 40,
      background: 'var(--bg-elevated)',
      border:     '1px solid var(--border)',
      padding:    '8px 12px',
      fontFamily: '"DM Mono", monospace',
      fontSize:   '11px',
      color:      'var(--text-secondary)',
      pointerEvents: 'none',
      zIndex:     100,
      whiteSpace: 'nowrap',
    }}>
      <div style={{ color: 'var(--text-primary)', marginBottom: '2px',
                    textTransform: 'uppercase', letterSpacing: '0.1em' }}>
        {tooltip.genre_a} + {tooltip.genre_b}
      </div>
      <div style={{ color: 'var(--text-ghost)' }}>
        {tooltip.count.toLocaleString()} manga share both genres
      </div>
    </div>
  );
}
```

---

### Step 5 — Zoom Controls Component

```jsx
function ZoomControls({ svgRef, dimensions }) {
  const handleZoom = (direction) => {
    const svg = d3.select(svgRef.current);
    const zoom = svgRef.current.__zoomBehavior;
    if (!zoom) return;
    svg.transition().duration(300).call(
      zoom.scaleBy, direction === 'in' ? 1.4 : 0.7
    );
  };

  const handleReset = () => {
    const svg = d3.select(svgRef.current);
    const zoom = svgRef.current.__zoomBehavior;
    if (!zoom) return;
    svg.transition().duration(400).call(
      zoom.transform,
      d3.zoomIdentity.translate(0, 0).scale(1)
    );
  };

  const btnStyle = {
    background:  'var(--bg-elevated)',
    border:      '1px solid var(--border)',
    color:       'var(--text-secondary)',
    fontFamily:  '"DM Mono", monospace',
    fontSize:    '12px',
    width:       '28px',
    height:      '28px',
    cursor:      'pointer',
    display:     'flex',
    alignItems:  'center',
    justifyContent: 'center',
  };

  return (
    <div style={{
      position: 'absolute',
      top: '12px',
      right: '12px',
      display: 'flex',
      gap: '4px',
      alignItems: 'center',
      zIndex: 5,
    }}>
      <button style={btnStyle} onClick={() => handleZoom('in')}>+</button>
      <button style={btnStyle} onClick={() => handleZoom('out')}>−</button>
      <button
        onClick={handleReset}
        style={{ ...btnStyle, width: 'auto', padding: '0 10px',
                 fontSize: '9px', letterSpacing: '0.1em',
                 textTransform: 'uppercase' }}
      >
        Reset view
      </button>
    </div>
  );
}
```

---

### Step 6 — Loading and Error States

```jsx
function LoadingState() {
  return (
    <div style={{
      position:       'absolute',
      inset:          0,
      display:        'flex',
      flexDirection:  'column',
      alignItems:     'center',
      justifyContent: 'center',
      gap:            '16px',
    }}>
      {/* Animated pulse rings */}
      <div style={{ position: 'relative', width: '60px', height: '60px' }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            position:     'absolute',
            inset:        0,
            borderRadius: '50%',
            border:       '1px solid var(--border)',
            animation:    `ping 1.5s ease-out ${i * 0.4}s infinite`,
          }} />
        ))}
      </div>
      <p style={{
        fontFamily: '"DM Mono", monospace',
        fontSize:   '11px',
        color:      'var(--text-ghost)',
        letterSpacing: '0.15em',
        textTransform: 'uppercase',
      }}>
        Computing genre relationships...
      </p>
      <style>{`
        @keyframes ping {
          0%   { transform: scale(0.5); opacity: 0.8; }
          100% { transform: scale(2.5); opacity: 0; }
        }
      `}</style>
    </div>
  );
}

function ErrorState({ error, onRetry }) {
  return (
    <div style={{
      position:       'absolute',
      inset:          0,
      display:        'flex',
      flexDirection:  'column',
      alignItems:     'center',
      justifyContent: 'center',
      gap:            '12px',
    }}>
      <p style={{ fontFamily: '"DM Mono"', fontSize: '11px',
                  color: 'var(--text-secondary)', textTransform: 'uppercase',
                  letterSpacing: '0.1em' }}>
        Genre data unavailable
      </p>
      <button
        onClick={onRetry}
        style={{ fontFamily: '"DM Mono"', fontSize: '10px',
                 color: 'var(--accent-red)', background: 'none',
                 border: '1px solid var(--accent-red)',
                 padding: '6px 14px', cursor: 'pointer',
                 textTransform: 'uppercase', letterSpacing: '0.1em' }}
      >
        Retry
      </button>
    </div>
  );
}
```

---

## Critical Rules Agent Must Follow

These are non-negotiable. Violating any one of them recreates the original bug.

| Rule | Why It Matters |
|---|---|
| Container div must have explicit `height: '600px'` | Without this, `clientHeight` is 0 when ResizeObserver fires |
| SVG must have explicit `width` and `height` attributes from state | CSS sizing does not work reliably with D3 |
| D3 `useEffect` must check `dimensions.width === 0` before running | Prevents simulation from initializing in zero space |
| forceCenter must use `width / 2, height / 2` from ResizeObserver | Never hardcode center coordinates |
| Nodes must be clamped to `[radius+10, width-radius-10]` on each tick | Prevents nodes from drifting off screen |
| `forceX` and `forceY` with strength 0.05 must be added | Provides gentle gravity to prevent scatter |
| SVG `selectAll('*').remove()` must run before re-drawing | Prevents duplicate SVG elements on dimension changes |
| `simRef.current.stop()` must run in useEffect cleanup | Prevents memory leaks and zombie simulations |

---

## Verification Steps

After implementing, verify in this exact order:

**Step 1 — Dimensions test:**
Open browser console and run:
```javascript
document.querySelector('.genre-network-container').getBoundingClientRect()
```
Width and height must both be non-zero before proceeding.

**Step 2 — API test:**
Check the Network tab in browser DevTools. `GET /genres/relationships`
must return 200 with a JSON body containing `nodes` and `edges` arrays.

**Step 3 — Render test:**
The SVG must show circles scattered across the full container area —
not clustered in one corner or invisible.

**Step 4 — Interaction test:**
Click any bubble. It should:
- Highlight its connections
- Dim everything else
- Show the detail panel sliding in from the right

**Step 5 — Resize test:**
Resize the browser window. The graph must re-render to fill the new size
without nodes escaping the viewport.

---

## What Must Not Change

| File | Status |
|---|---|
| `GenreHeatmap.jsx` | Unchanged |
| `ChartsPage.jsx` | Unchanged |
| `backend/main.py` | Unchanged |
| All CSS/design tokens | Unchanged |
| URL state filter system | Unchanged |
| All other app features | Unchanged |
