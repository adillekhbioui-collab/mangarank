import sys

file_path = "C:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/App.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_genre_picker = """// ── Reusable searchable genre picker ──
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
}"""

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
}"""

if old_genre_picker in content:
    content = content.replace(old_genre_picker, new_genre_picker)
else:
    print("WARNING: Could not find old GenrePicker code.")
    import re
    app_re = re.sub(r'\s+', r'\\s+', old_genre_picker)
    if re.search(app_re, content):
        content = re.sub(app_re, new_genre_picker, content)
    else:
        sys.exit(1)


old_usage = """                    <GenrePicker
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
                    />"""

new_usage = """                    <UnifiedGenrePicker
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

if old_usage in content:
    content = content.replace(old_usage, new_usage)
else:
    print("WARNING: Could not find old usage code.")
    import re
    app_re = re.sub(r'\s+', r'\\s+', old_usage)
    if re.search(app_re, content):
        content = re.sub(app_re, new_usage, content)
    else:
        sys.exit(1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("App.jsx rewritten successfully.")