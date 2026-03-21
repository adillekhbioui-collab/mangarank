file_path = "src/index.css"

with open(file_path, "r", encoding="utf-8") as f:
    css = f.read()

grid_css = """
/* ────────────────────────────────────────────────────────── */
/* GRID VIEW                                                  */
/* ────────────────────────────────────────────────────────── */

/* View toggle buttons */
.view-toggle-btn {
  font-family: var(--font-data);
  font-size: 11px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 6px 12px;
  cursor: pointer;
  transition: all .2s ease;
}
.view-toggle-btn:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}
.view-toggle-btn.active {
  background: var(--text-primary);
  color: var(--bg-primary);
  border-color: var(--text-primary);
}

.manga-grid {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 16px;
  width: 100%;
}

.manga-grid .manga-strip {
  flex-direction: column;
  height: auto;
  border-left: none;
  background: transparent;
  position: relative;
  overflow: hidden;
  padding: 0;
  /* Make items respond to width up to a minimum bound */
  flex: 1 1 calc(20% - 16px);
  min-width: 140px;
  max-width: 250px;
}

.manga-grid .manga-strip:hover {
  background: var(--bg-secondary);
}

/* Adjust Cover to fill top of card */
.manga-grid .strip-cover-col {
  width: 100%;
  aspect-ratio: 2/3;
  height: auto;
}
.manga-grid .strip-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Adjust internal layout */
.manga-grid .strip-meta-col {
  padding: 12px 0;
}

.manga-grid .strip-genres {
  flex-wrap: wrap;
  max-height: 48px;
  overflow: hidden;
}

/* Hide or absolute position elements for grid */
.manga-grid .strip-rank-col {
  position: absolute;
  top: 8px;
  left: 8px;
  width: auto;
  z-index: 10;
  background: rgba(13, 11, 14, 0.8);
  padding: 2px 6px;
  border-radius: 4px;
}
.manga-grid .strip-rank {
  font-size: 16px;
  color: white;
}

.manga-grid .strip-score-col {
  position: absolute;
  top: 8px;
  right: 8px;
  width: auto;
  padding: 4px 6px;
  z-index: 10;
  background: rgba(13, 11, 14, 0.9);
  flex-direction: row;
  gap: 4px;
  align-items: center;
  border: 1px solid var(--border);
}

.manga-grid .strip-score {
  font-size: 14px;
}
.manga-grid .score-label {
  display: none;
}
"""

if "/* GRID VIEW" not in css:
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(grid_css)
    print("index.css updated.")
else:
    print("Grid CSS already exists.")
