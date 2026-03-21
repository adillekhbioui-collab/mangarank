with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/App.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace GenrePicker
new_genre_picker = """// ── Reusable searchable genre picker ──
function GenrePicker({ label, type, selected, onToggle, onClear, onResetDefault, allGenres, otherSelected, maxSelections }) {
    const [search, setSearch] = useState('')

    const filtered = allGenres.filter(g =>
        g.toLowerCase().includes(search.toLowerCase()) &&
        !otherSelected.has(g)
    )

    return (
        <div className="filter-section">
            <div className="filter-label">
                {label} {maxSelections && `(Max ${maxSelections})`}
            </div>
            
            <input
                className="genre-input"
                placeholder="Search genres..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
            />
            
            {selected.length > 0 && (
                <div className="genre-tags" style={{ marginBottom: '8px' }}>
                    {selected.map(g => (
                        <div key={g} className={`genre-tag ${type}`} onClick={() => onToggle(g)}>
                            {g} <span className="remove">×</span>
                        </div>
                    ))}
                </div>
            )}

            {search && filtered.length > 0 && (
                <div className="genre-tags" style={{ marginTop: '8px' }}>
                    {filtered.slice(0, 10).map(g => {
                        const isSelected = selected.includes(g)
                        const isDisabled = Boolean(maxSelections) && !isSelected && selected.length >= maxSelections
                        if (isSelected) return null
                        return (
                            <div
                                key={g}
                                className={`genre-tag`}
                                style={{ opacity: isDisabled ? 0.5 : 1, cursor: isDisabled ? 'not-allowed' : 'pointer' }}
                                onClick={() => !isDisabled && onToggle(g)}
                            >
                                + {g}
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
"""

start_idx = text.find("// ── Reusable searchable genre picker ──")
end_idx = text.find("function HomePage() {")
text = text[:start_idx] + new_genre_picker + text[end_idx:]

new_return = """    return (
        <>
            <header className="site-header">
                <div className="header-left">
                    <Link to="/" className="logo" onClick={() => updateMainFilters({}, 'push')}>
                        <span className="logo-manhwa">MANHWA</span>
                        <span className="logo-rank">RANK</span>
                    </Link>
                </div>
                
                <div className="header-center">
                    <div className="nav-tabs">
                        <span className={`nav-tab ${category==='' ? 'active' : ''}`} onClick={() => handleQuickFilter('')}>ALL</span>
                        <span className={`nav-tab ${category==='manhwa' ? 'active' : ''}`} onClick={() => handleQuickFilter('manhwa')}>MANHWA</span>
                        <span className={`nav-tab ${category==='manhua' ? 'active' : ''}`} onClick={() => handleQuickFilter('manhua')}>MANHUA</span>
                        <span className={`nav-tab ${category==='masterpieces' ? 'active' : ''}`} onClick={() => handleQuickFilter('masterpieces')}>MASTERPIECES</span>
                        <span className="nav-tab">CHARTS</span>
                    </div>
                </div>

                <div className="header-right">
                    <input
                        className="search-input"
                        type="text"
                        placeholder="Search titles..."
                        value={searchInput}
                        onFocus={() => { searchCommitBaseRef.current = search }}
                        onChange={(e) => handleSearchChange(e.target.value)}
                        onBlur={commitSearch}
                        onKeyDown={handleSearchKeyDown}
                    />
                </div>
            </header>

            <div className="category-strip">
                {QUICK_FILTERS.map(({ label, category: quickCategory }) => (
                    <div 
                        key={quickCategory}
                        className={`category-card ${activeQuickFilter === quickCategory ? 'active' : ''}`}
                        data-cat={quickCategory}
                        onClick={() => handleQuickFilter(quickCategory)}
                    >
                        <div className="cat-name">{label.replace(/[^a-zA-Z\\s]/g, '').trim()}</div>
                        <div className="cat-count">VIEW CATEGORY</div>
                    </div>
                ))}
            </div>

            <div className="main-layout">
                {/* ── Filter Panel ── */}
                <aside className="filter-panel">
                    <GenrePicker
                        label="Include" type="include"
                        selected={genreInclude} onToggle={toggleInclude} onClear={clearInclude}
                        maxSelections={MAX_INCLUDE_GENRES}
                        allGenres={genres} otherSelected={new Set(genreExclude)}
                    />
                    <GenrePicker
                        label="Exclude" type="exclude"
                        selected={genreExclude} onToggle={toggleExclude} onClear={clearExclude}
                        maxSelections={MAX_EXCLUDE_GENRES}
                        allGenres={genres} otherSelected={new Set(genreInclude)}
                    />

                    <div className="filter-section">
                        <div className="filter-label">Status</div>
                        {['', 'ongoing', 'completed'].map((v) => (
                            <span 
                                key={v} 
                                className={`filter-status-option ${status === v ? 'active' : ''}`}
                                onClick={() => updateMainFilters({ status: v })}
                            >
                                {v === '' ? 'ALL' : v}
                            </span>
                        ))}
                    </div>

                    <div className="filter-section">
                        <div className="filter-label">Sort By</div>
                        <select className="filter-select" value={sortBy} onChange={(e) => updateMainFilters({ sort_by: e.target.value })}>
                            <option value="score">Best Score</option>
                            <option value="views">Most Popular</option>
                            <option value="chapters">Most Chapters</option>
                            <option value="completion">Completion Rate</option>
                        </select>
                    </div>

                    <div className="filter-section" style={{ borderBottom: 'none' }}>
                        <div className="filter-label">Min Chapters</div>
                        <input
                            className="filter-number"
                            type="number"
                            min="0"
                            value={minChaptersInput}
                            onFocus={() => { minCommitBaseRef.current = minChapters }}
                            onChange={(e) => handleMinChaptersChange(e.target.value)}
                            onBlur={commitMinChapters}
                            onKeyDown={handleMinChaptersKeyDown}
                        />
                    </div>
                </aside>

                {/* ── Main Content ── */}
                <main className="content-area">
                    {loading && (
                        <div className="manga-list">
                            {Array.from({ length: 8 }).map((_, i) => (
                                <div key={i} className="skeleton-strip" />
                            ))}
                        </div>
                    )}

                    {!loading && results.length === 0 && (
                        <div style={{ padding: '48px', textAlign: 'center', fontFamily: 'var(--font-data)', color: 'var(--text-secondary)' }}>
                            NO RESULTS FOUND.
                        </div>
                    )}

                    {!loading && results.length > 0 && (
                        <>
                            <div className="manga-list">
                                {results.map((m, i) => {
                                    const rank = (page - 1) * LIMIT + i + 1;
                                    const badgeLabel = m.status ? m.status : 'ONGOING';
                                    let scoreColorClass = 'low';
                                    if (m.aggregated_score >= 90) scoreColorClass = 'gold';
                                    else if (m.aggregated_score >= 75) scoreColorClass = 'normal';
                                    
                                    return (
                                        <Link
                                            key={`${m.title}-${i}`}
                                            to={`/manga/${encodeURIComponent(m.title)}`}
                                            className="manga-strip"
                                        >
                                            <div className="strip-rank-col">
                                                <span className="strip-rank">{rank}</span>
                                            </div>
                                            <div className="strip-cover-col">
                                                <img 
                                                    className="strip-cover"
                                                    src={m.cover_image
                                                        ? `${API_BASE}/proxy/image?url=${encodeURIComponent(m.cover_image)}`
                                                        : 'https://placehold.co/110x160/1C1822/3D3545?text=No+Cover'
                                                    }
                                                    alt={m.title}
                                                    loading="lazy"
                                                />
                                            </div>
                                            <div className="strip-meta-col">
                                                <h3 className="strip-title">{m.title}</h3>
                                                <div className="strip-author">{m.author || 'Unknown Author'}</div>
                                                <div className="strip-genres">
                                                    {(m.genres || []).slice(0, 4).join(' · ')}
                                                </div>
                                                <div className="strip-stats">
                                                    <span>{m.chapter_count || 0} ch.</span>
                                                    <span>|</span>
                                                    <span>{m.total_views ? m.total_views.toLocaleString() : '0'} views</span>
                                                    <span className={`strip-status ${badgeLabel.toLowerCase()}`}>{badgeLabel}</span>
                                                </div>
                                            </div>
                                            <div className="strip-score-col">
                                                <div className={`strip-score ${scoreColorClass}`}>
                                                    {m.aggregated_score != null ? Math.round(m.aggregated_score) : '—'}
                                                </div>
                                                <div className="score-label">SCORE</div>
                                            </div>
                                        </Link>
                                    );
                                })}
                            </div>

                            {!activeQuickFilter && totalPages > 1 && (
                                <div className="pagination">
                                    <button className="page-btn" disabled={page <= 1} onClick={() => updatePage(page - 1)}>
                                        PREV
                                    </button>
                                    {getPageNumbers().map((p, i) =>
                                        p === '...' ? (
                                            <span key={`e${i}`} className="page-num ellipsis">…</span>
                                        ) : (
                                            <span key={p}
                                                className={`page-num ${p === page ? 'active' : ''}`}
                                                style={{cursor: 'pointer'}}
                                                onClick={() => updatePage(p)}>
                                                {p}
                                            </span>
                                        )
                                    )}
                                    <button className="page-btn" disabled={page >= totalPages} onClick={() => updatePage(Math.min(totalPages, page + 1))}>
                                        NEXT
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </main>
            </div>
        </>
    )
}

export default function App() {"""

start_ret = text.find("    return (\n        <>\n            {/* ── Header ── */}")
end_ret = text.find("export default function App() {")

text = text[:start_ret] + new_return + text[end_ret + len("export default function App() {"):]

with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(text)
