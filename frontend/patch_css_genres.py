import sys

file_path = "C:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/index.css"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_css = """
/* ────────────────────────────────────────────────────────── */
/* UNIFIED TRI-STATE GENRES                                   */
/* ────────────────────────────────────────────────────────── */
.genres-summary { margin-bottom: 16px; }
.genres-summary-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
  font-family: var(--font-data);
  font-size: 10px;
  color: var(--text-secondary);
}
.genres-summary-label { width: 50px; font-weight: bold; }
.summary-tag {
  border: 1px solid var(--border);
  padding: 2px 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.summary-tag.include { border-color: var(--accent-red); color: var(--accent-red); background: rgba(193, 18, 31, 0.08); }
.summary-tag.exclude { border-color: var(--text-ghost); color: var(--text-ghost); text-decoration: line-through; border-style: dashed; }
.summary-tag .remove { cursor: pointer; opacity: 0.7; }
.summary-tag .remove:hover { opacity: 1; }

.genre-grid-toggle {
  font-family: var(--font-data);
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.genre-grid-toggle:hover { color: var(--text-primary); }

.genre-grid-container {
  overflow: hidden;
}

.genre-grid-search {
  width: 100%;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  color: var(--text-primary);
  font-family: var(--font-data);
  font-size: 12px;
  padding: 6px 0;
  outline: none;
  margin-bottom: 12px;
}

.genre-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.genre-chip {
  font-family: var(--font-data);
  font-size: 10px;
  text-transform: uppercase;
  padding: 5px 10px;
  border: 1px solid var(--border);
  background: transparent;
  border-radius: 2px;
  cursor: pointer;
  transition: all 120ms ease;
  user-select: none;
}
@media (max-width: 768px) {
  .genre-chip { min-height: 32px; display: flex; align-items: center; }
}

.genre-chip.neutral {
  color: var(--text-secondary);
  border: 1px solid var(--border);
  text-decoration: none;
}
.genre-chip.neutral:hover {
  border-color: var(--text-ghost);
  color: var(--text-primary);
}

.genre-chip.include {
  color: var(--accent-red);
  border: 1px solid var(--accent-red);
  background: rgba(193, 18, 31, 0.08);
  text-decoration: none;
}

.genre-chip.exclude {
  color: var(--text-ghost);
  border: 1px dashed var(--border);
  background: transparent;
  text-decoration: line-through;
}

.genre-chip.default-exclude {
  color: var(--text-ghost);
  border: 1px solid var(--border);
  background: rgba(0, 0, 0, 0.2);
}

.filter-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.clear-all-link {
  font-family: var(--font-data);
  font-size: 10px;
  color: var(--text-ghost);
  cursor: pointer;
  text-transform: uppercase;
  text-decoration: underline;
}
.clear-all-link:hover { color: var(--text-primary); }
"""

if "UNIFIED TRI-STATE" not in content:
    content += new_css

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("index.css rewritten successfully.")
