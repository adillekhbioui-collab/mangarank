import sys

file_path = "C:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/App.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Find the start of GenrePicker
start_idx = content.find("// ── Reusable searchable genre picker ──")
if start_idx == -1:
    print("Could not find start of GenrePicker")
    sys.exit(1)

# Find the end of GenrePicker, which is right before "function HomePage()"
end_idx = content.find("function HomePage()", start_idx)
if end_idx == -1:
    print("Could not find end of GenrePicker")
    sys.exit(1)

old_genre_picker_actual = content[start_idx:end_idx]

new_genre_picker = """// ── Unified Tri-State Genre Picker ──
function UnifiedGenrePicker({
    allGenres,
    blacklistedGenres,
    include,
    exclude,
    excludeMode,
    onToggleState,
    onClearAll,
    maxInclude,
    maxExclude
}) {
    const hasActiveFilters = include.length > 0 || exclude.length > 0
    const [isExpanded, setIsExpanded] = useState(hasActiveFilters)
    const [search, setSearch] = useState('')

    const includeSet = new Set(include)
    const excludeSet = new Set(exclude)
    const defaultExcludeSet = excludeMode === 'default' ? new Set(blacklistedGenres) : new Set()

    const sortedGenres = useMemo(() => {
        return [...allGenres].sort((a, b) => {
            const aActive = includeSet.has(a) || excludeSet.has(a) || defaultExcludeSet.has(a)
            const bActive = includeSet.has(b) || excludeSet.has(b) || defaultExcludeSet.has(b)
            if (aActive && !bActive) return -1
            if (!aActive && bActive) return 1
            return a.localeCompare(b)
        })
    }, [allGenres, includeSet, excludeSet, defaultExcludeSet])

    const filteredGenres = search
        ? sortedGenres.filter(g => g.toLowerCase().includes(search.toLowerCase()))
        : sortedGenres

    return (
        <div className="filter-section">
            <div className="filter-header-row">
                <div className="filter-label" style={{ marginBottom: 0 }}>GENRES</div>
                {hasActiveFilters && (
                    <span className="clear-all-link" onClick={onClearAll}>Clear all</span>
                )}
            </div>

            {hasActiveFilters && (
                <div className="genres-summary">
                    {include.length > 0 && (
                        <div className="genres-summary-line">
                            <span className="genres-summary-label">INCLUDE:</span>
                            {include.map(g => (
                                <span key={g} className="summary-tag include" onClick={() => onToggleState(g)}>
                                    {g} <span className="remove">×</span>
                                </span>
                            ))}
                        </div>
                    )}
                    {exclude.length > 0 && (
                        <div className="genres-summary-line">
                            <span className="genres-summary-label">EXCLUDE:</span>
                            {exclude.map(g => (
                                <span key={g} className="summary-tag exclude" onClick={() => onToggleState(g)}>
                                    {g} <span className="remove">×</span>
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            )}

            <button className="genre-grid-toggle" onClick={() => setIsExpanded(!isExpanded)}>
                {isExpanded ? 'HIDE GENRES' : 'SHOW ALL GENRES'} 
                <span>{isExpanded ? '▲' : '▼'}</span>
            </button>

            {isExpanded && (
                <div className="genre-grid-container">
                    <input
                        className="genre-grid-search"
                        placeholder="Filter genres..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <div className="genre-grid">
                        {filteredGenres.map(g => {
                            let stateClass = 'neutral'
                            let prefix = ''
                            if (includeSet.has(g)) {
                                stateClass = 'include'
                                prefix = '+ '
                            } else if (excludeSet.has(g)) {
                                stateClass = 'exclude'
                                prefix = '– '
                            } else if (defaultExcludeSet.has(g)) {
                                stateClass = 'default-exclude'
                                prefix = '– '
                            }

                            return (
                                <div
                                    key={g}
                                    className={`genre-chip ${stateClass}`}
                                    onClick={() => onToggleState(g)}
                                    title={stateClass === 'default-exclude' ? 'Excluded by default (click to include)' : ''}
                                >
                                    {prefix}{g}
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}
        </div>
    )
}
"""

content = content.replace(old_genre_picker_actual, new_genre_picker)


usage_start = content.find("<GenrePicker")
if usage_start == -1:
    print("Could not find <GenrePicker usage")
    sys.exit(1)

usage_end = content.find("/>", content.find("<GenrePicker", usage_start + 1)) + 2

old_usage_actual = content[usage_start:usage_end]


new_usage = """<UnifiedGenrePicker
                        allGenres={genres}
                        blacklistedGenres={blacklistedGenres}
                        include={genreInclude}
                        exclude={genreExclude}
                        excludeMode={filters.exclude_mode}
                        onToggleState={(g) => {
                            if (genreInclude.includes(g)) {
                                if (genreExclude.length >= MAX_EXCLUDE_GENRES) return;
                                updateMainFilters({
                                    genre_include: genreInclude.filter(x => x !== g),
                                    genre_exclude: [...genreExclude, g],
                                    exclude_mode: 'custom'
                                })
                            } else if (genreExclude.includes(g)) {
                                updateMainFilters({
                                    genre_exclude: genreExclude.filter(x => x !== g),
                                    exclude_mode: 'custom'
                                })
                            } else {
                                if (genreInclude.length >= MAX_INCLUDE_GENRES) return;
                                updateMainFilters({
                                    genre_include: [...genreInclude, g]
                                })
                            }
                        }}
                        onClearAll={() => updateMainFilters({ genre_include: [], genre_exclude: [], exclude_mode: 'custom' })}
                        maxInclude={MAX_INCLUDE_GENRES}
                        maxExclude={MAX_EXCLUDE_GENRES}
                    />"""

content = content.replace(old_usage_actual, new_usage)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("App.jsx rewritten successfully.")
