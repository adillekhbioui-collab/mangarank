import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useTheme } from './hooks/useTheme.js'

import { Routes, Route, Link, useSearchParams } from 'react-router-dom'
import { fetchManga, fetchGenres, fetchBlacklistedGenres, fetchTopCategory, API_BASE } from './api'
import MangaDetailPage from './MangaDetailPage.jsx'
import GenreUniverseSection from './components/charts/GenreUniverseSection.jsx'
import { WatchlistSection } from './components/WatchlistSection.jsx'
import { WatchlistButton } from './components/WatchlistButton.jsx'

const QUICK_FILTERS = [
    { label: '⭐ Masterpieces', category: 'masterpieces', apiCategory: 'completion-masterpieces', desc: 'High quality manga that most readers finish.' },
    { label: '⚠️ Hard to Finish', category: 'hard-to-finish', apiCategory: 'completion-traps', desc: 'Highly rated manga that most readers drop.' },
    { label: '🍿 Guilty Pleasures', category: 'guilty-pleasures', desc: 'Lower-rated manga that readers keep finishing anyway.' },
    { label: '🔥 Top Action', category: 'action', desc: '' },
    { label: '✨ Top Fantasy', category: 'fantasy', desc: '' },
    { label: '✅ Completed', category: 'completed', desc: '' },
    { label: '🆕 Recently Added', category: 'recent', desc: 'Latest titles added to the collection.' },
]

const QUICK_FILTER_MAP = new Map(
    QUICK_FILTERS.map((item) => [
        item.category,
        { ...item, apiCategory: item.apiCategory || item.category },
    ]),
)

const ALLOWED_SORTS = new Set(['score', 'views', 'chapters', 'completion'])
const ALLOWED_STATUS = new Set(['', 'ongoing', 'completed'])
const MAX_INCLUDE_GENRES = 10
const MAX_EXCLUDE_GENRES = 100
const LIMIT = 30

const DEFAULT_FILTERS = {
    page: 1,
    sort_by: 'views', // Changed from 'score' to 'views'
    status: '',
    min_chapters: 0,
    genre_include: [],
    genre_exclude: [],
    exclude_mode: 'default',
    search: '',
    has_completion: false,
    category: '',
}

function toPositiveInt(value, fallback) {
    const n = Number.parseInt(value, 10)
    return Number.isFinite(n) && n > 0 ? n : fallback
}

function toNonNegativeInt(value, fallback) {
    const n = Number.parseInt(value, 10)
    return Number.isFinite(n) && n >= 0 ? n : fallback
}

function normalizeGenres(values, allowedGenresSet, blockedGenresSet, maxGenres = Number.POSITIVE_INFINITY) {
    const out = []
    const seen = new Set()

    values.forEach((g) => {
        if (!g || seen.has(g) || out.length >= maxGenres) return
        if (allowedGenresSet && allowedGenresSet.size > 0 && !allowedGenresSet.has(g)) return
        if (blockedGenresSet && blockedGenresSet.has(g)) return
        seen.add(g)
        out.push(g)
    })

    return out
}

function getFiltersFromURL(searchParams, genres, blacklistedGenres) {
    const allowedCategories = new Set(QUICK_FILTER_MAP.keys())
    const allowedGenresSet = new Set(genres)

    const page = toPositiveInt(searchParams.get('page'), DEFAULT_FILTERS.page)

    const rawSort = searchParams.get('sort_by') || DEFAULT_FILTERS.sort_by
    const sort_by = ALLOWED_SORTS.has(rawSort) ? rawSort : DEFAULT_FILTERS.sort_by

    const rawStatus = searchParams.get('status') || DEFAULT_FILTERS.status
    const status = ALLOWED_STATUS.has(rawStatus) ? rawStatus : DEFAULT_FILTERS.status

    const min_chapters = toNonNegativeInt(
        searchParams.get('min_chapters'),
        DEFAULT_FILTERS.min_chapters,
    )

    const has_completion = searchParams.get('has_completion') === 'true'
    const search = (searchParams.get('search') || '').trim()

    const rawCategory = searchParams.get('category') || ''
    const category = allowedCategories.has(rawCategory) ? rawCategory : ''

    const includeFromURL = searchParams.getAll('genre_include')
    const excludeFromURL = searchParams.getAll('genre_exclude')
    const exclude_mode = searchParams.get('exclude_mode') === 'custom' ? 'custom' : 'default'

    const genre_include = normalizeGenres(includeFromURL, allowedGenresSet, null, MAX_INCLUDE_GENRES)
    const blockedGenres = new Set(genre_include)

    let genre_exclude = normalizeGenres(excludeFromURL, allowedGenresSet, blockedGenres, MAX_EXCLUDE_GENRES)
    const hasExplicitExclude = searchParams.has('genre_exclude')

    if (exclude_mode !== 'custom' && !hasExplicitExclude) {
        genre_exclude = normalizeGenres(blacklistedGenres, allowedGenresSet, blockedGenres, MAX_EXCLUDE_GENRES)
    }

    return {
        page,
        sort_by,
        status,
        min_chapters,
        genre_include,
        genre_exclude,
        exclude_mode,
        search,
        has_completion,
        category,
    }
}

function buildURLSearchParams(filters) {
    const params = new URLSearchParams()

    if (filters.page > DEFAULT_FILTERS.page) params.set('page', String(filters.page))
    if (filters.sort_by !== DEFAULT_FILTERS.sort_by) params.set('sort_by', filters.sort_by)
    if (filters.status) params.set('status', filters.status)
    if (filters.min_chapters > DEFAULT_FILTERS.min_chapters) params.set('min_chapters', String(filters.min_chapters))
    if (filters.search) params.set('search', filters.search)
    if (filters.has_completion) params.set('has_completion', 'true')
    if (filters.category) params.set('category', filters.category)
    if (filters.exclude_mode === 'custom') params.set('exclude_mode', 'custom')

    filters.genre_include.forEach((g) => params.append('genre_include', g))
    if (filters.exclude_mode === 'custom') {
        filters.genre_exclude.forEach((g) => params.append('genre_exclude', g))
    }

    return params
}

// ── Unified Tri-State Genre Picker ──
function UnifiedGenrePicker({
    allGenres,
    defaultExcludedGenres,
    include,
    manualExclude,
    onToggleState,
    onClearAll,
    maxInclude,
    maxExclude
}) {
    const hasActiveFilters = include.length > 0 || manualExclude.length > 0
    const [isExpanded, setIsExpanded] = useState(hasActiveFilters)
    const [search, setSearch] = useState('')

    const includeSet = new Set(include)
    const manualExcludeSet = new Set(manualExclude)
    const defaultExcludeSet = new Set(defaultExcludedGenres)

    const sortedGenres = useMemo(() => {
        return [...allGenres].sort((a, b) => {
            const aActive = includeSet.has(a) || manualExcludeSet.has(a)
            const bActive = includeSet.has(b) || manualExcludeSet.has(b)
            const aDefault = !aActive && defaultExcludeSet.has(a)
            const bDefault = !bActive && defaultExcludeSet.has(b)
            
            if (aActive && !bActive) return -1
            if (!aActive && bActive) return 1
            if (aDefault && !bDefault) return 1
            if (!aDefault && bDefault) return -1
            
            return a.localeCompare(b)
        })
    }, [allGenres, includeSet, manualExcludeSet, defaultExcludeSet])

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
                    {manualExclude.length > 0 && (
                        <div className="genres-summary-line">
                            <span className="genres-summary-label">EXCLUDE:</span>
                            {manualExclude.map(g => (
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
                            } else if (manualExcludeSet.has(g)) {
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
function HomePage({ initialTopTab = 'browse' }) {
    const [searchParams, setSearchParams] = useSearchParams()
    const { theme, toggleTheme, isDark } = useTheme()
    const [topTab, setTopTab] = useState(initialTopTab)
    const [isHeaderHidden, setIsHeaderHidden] = useState(false)

    // ── Local UI state ──
    const [viewMode, setViewMode] = useState('list')
    const [touchStart, setTouchStart] = useState(null)
    const [touchEnd, setTouchEnd] = useState(null)

    const onTouchStart = (e) => {
        setTouchEnd(null)
        setTouchStart(e.targetTouches[0].clientX)
    }

    const onTouchMove = (e) => setTouchEnd(e.targetTouches[0].clientX)

    const onTouchEnd = () => {
        if (!touchStart || !touchEnd) return
        const distance = touchStart - touchEnd
        const isLeftSwipe = distance > 50
        const isRightSwipe = distance < -50
        if (isLeftSwipe && viewMode === 'list') setViewMode('grid')
        if (isRightSwipe && viewMode === 'grid') setViewMode('list')
    }
    const [results, setResults] = useState([])
    const [genres, setGenres] = useState([])
    const [blacklistedGenres, setBlacklistedGenres] = useState([])
    const [loading, setLoading] = useState(true)
    const [totalPages, setTotalPages] = useState(1)
    const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false)
    const [searchInput, setSearchInput] = useState('')
    const [minChaptersInput, setMinChaptersInput] = useState('0')
    const [copied, setCopied] = useState(false)

    const searchCommitBaseRef = useRef('')
    const minCommitBaseRef = useRef(0)
    const copyTimeoutRef = useRef(null)
    const lastScrollYRef = useRef(0)
    const scrollFrameRef = useRef(null)

    const filters = useMemo(
        () => getFiltersFromURL(searchParams, genres, blacklistedGenres),
        [searchParams, genres, blacklistedGenres],
    )

    const {
        page,
        sort_by: sortBy,
        status,
        min_chapters: minChapters,
        genre_include: genreInclude,
        genre_exclude: genreExclude,
        search,
        has_completion: hasCompletionData,
        category,
    } = filters

    const activeQuickFilter = category || null
    const isCategoryMode = Boolean(activeQuickFilter)
    const activeFilterCount = useMemo(() => {
        let count = 0
        if (genreInclude.length > 0) count += 1
        if (status) count += 1
        if (sortBy !== DEFAULT_FILTERS.sort_by) count += 1
        if (minChapters > 0) count += 1
        if (search) count += 1
        return count
    }, [genreInclude.length, status, sortBy, minChapters, search])

    const applyURL = useCallback((nextFilters, mode = 'push') => {
        setSearchParams(buildURLSearchParams(nextFilters), { replace: mode === 'replace' })
    }, [setSearchParams])

    const updatePage = useCallback((nextPage, mode = 'push') => {
        applyURL(
            {
                ...filters,
                page: Math.max(1, Number.parseInt(nextPage, 10) || 1),
            },
            mode,
        )
    }, [applyURL, filters])

    const updateMainFilters = useCallback((partial, mode = 'push') => {
        const merged = {
            ...filters,
            ...partial,
            page: 1,
            category: '',
        }
        applyURL(merged, mode)
    }, [applyURL, filters])

    const updateCategory = useCallback((nextCategory) => {
        if (!nextCategory || !QUICK_FILTER_MAP.has(nextCategory)) {
            applyURL({ ...DEFAULT_FILTERS }, 'push')
            return
        }
        applyURL({ ...DEFAULT_FILTERS, category: nextCategory }, 'push')
    }, [applyURL])

    // ── Genre add/remove handlers ──
    const toggleInclude = (g) => {
        if (genreInclude.includes(g)) {
            updateMainFilters({ genre_include: genreInclude.filter((x) => x !== g) })
            return
        }
        if (genreInclude.length >= MAX_INCLUDE_GENRES) return
        updateMainFilters({ genre_include: [...genreInclude, g] })
    }

    const toggleExclude = (g) => {
        if (genreExclude.includes(g)) {
            updateMainFilters({ genre_exclude: genreExclude.filter((x) => x !== g), exclude_mode: 'custom' })
            return
        }
        if (genreExclude.length >= MAX_EXCLUDE_GENRES) return
        updateMainFilters({ genre_exclude: [...genreExclude, g], exclude_mode: 'custom' })
    }

    const blacklistedGenresSet = useMemo(() => new Set(blacklistedGenres), [blacklistedGenres])

    const defaultExcludedGenres = useMemo(() => {
        if (filters.exclude_mode !== 'default') return []
        return blacklistedGenres.filter((g) => !genreInclude.includes(g))
    }, [filters.exclude_mode, blacklistedGenres, genreInclude])

    const manualGenreExclude = useMemo(() => {
        if (filters.exclude_mode === 'default') {
            return genreExclude.filter((g) => !blacklistedGenresSet.has(g))
        }
        return genreExclude
    }, [filters.exclude_mode, genreExclude, blacklistedGenresSet])

    const clearInclude = () => updateMainFilters({ genre_include: [] })
    const clearExclude = () => updateMainFilters({ genre_exclude: [], exclude_mode: 'custom' })
    const clearAllGenres = () => updateMainFilters({ genre_include: [], genre_exclude: [], exclude_mode: 'custom' })
    const resetExcludeToDefault = () => updateMainFilters({ genre_exclude: [], exclude_mode: 'default' })

    const commitSearch = () => {
        const committed = searchInput.trim()
        if (committed === searchCommitBaseRef.current) return
        updateMainFilters({ search: committed }, 'push')
        searchCommitBaseRef.current = committed
    }

    const commitMinChapters = () => {
        const next = toNonNegativeInt(minChaptersInput, 0)
        if (next === minCommitBaseRef.current) return
        updateMainFilters({ min_chapters: next }, 'push')
        minCommitBaseRef.current = next
    }

    const handleCopyLink = async () => {
        try {
            await navigator.clipboard.writeText(window.location.href)
            setCopied(true)
            if (copyTimeoutRef.current) {
                clearTimeout(copyTimeoutRef.current)
            }
            copyTimeoutRef.current = setTimeout(() => setCopied(false), 1200)
        } catch {
            setCopied(false)
        }
    }

    // ── Load genres and blacklist defaults on mount ──
    useEffect(() => {
        let mounted = true

        Promise.all([
            fetchGenres(),
            fetchBlacklistedGenres().catch(() => []),
        ])
            .then(([allGenres, blacklist]) => {
                if (!mounted) return
                setGenres(allGenres || [])
                setBlacklistedGenres(blacklist || [])
            })
            .catch(() => {
                if (!mounted) return
                setGenres([])
                setBlacklistedGenres([])
            })

        return () => {
            mounted = false
        }
    }, [])

    useEffect(() => {
        setSearchInput(search)
        searchCommitBaseRef.current = search
    }, [search])

    useEffect(() => {
        setMinChaptersInput(String(minChapters))
        minCommitBaseRef.current = minChapters
    }, [minChapters])

    useEffect(() => {
        return () => {
            if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current)
        }
    }, [])

    useEffect(() => {
        document.body.classList.toggle('sheet-open', isMobileFilterOpen)
        return () => document.body.classList.remove('sheet-open')
    }, [isMobileFilterOpen])

    useEffect(() => {
        if (isMobileFilterOpen) {
            setIsHeaderHidden(false)
            return
        }

        lastScrollYRef.current = window.scrollY || 0

        const onScroll = () => {
            if (scrollFrameRef.current != null) return

            scrollFrameRef.current = window.requestAnimationFrame(() => {
                const currentScrollY = window.scrollY || 0
                const delta = currentScrollY - lastScrollYRef.current

                if (currentScrollY <= 8) {
                    setIsHeaderHidden(false)
                } else if (delta > 10 && currentScrollY > 72) {
                    setIsHeaderHidden(true)
                } else if (delta < -4) {
                    setIsHeaderHidden(false)
                }

                lastScrollYRef.current = currentScrollY
                scrollFrameRef.current = null
            })
        }

        window.addEventListener('scroll', onScroll, { passive: true })

        return () => {
            window.removeEventListener('scroll', onScroll)
            if (scrollFrameRef.current != null) {
                window.cancelAnimationFrame(scrollFrameRef.current)
                scrollFrameRef.current = null
            }
        }
    }, [isMobileFilterOpen])

    useEffect(() => {
        document.body.classList.toggle('header-hidden', isHeaderHidden && !isMobileFilterOpen)
        return () => document.body.classList.remove('header-hidden')
    }, [isHeaderHidden, isMobileFilterOpen])

    // ── Fetch manga whenever URL filters change ──
    const loadManga = useCallback(async () => {
        setLoading(true)

        if (category) {
            const quick = QUICK_FILTER_MAP.get(category)
            try {
                const data = await fetchTopCategory(quick.apiCategory)
                setResults(data || [])
                setTotalPages(1)
            } catch {
                setResults([])
                setTotalPages(1)
            }
            setLoading(false)
            return
        }

        try {
            const data = await fetchManga({
                genre_include: genreInclude.length > 0 ? genreInclude : undefined,
                genre_exclude: genreExclude.length > 0 ? genreExclude : undefined,
                status,
                sort_by: sortBy,
                has_completion_data: hasCompletionData,
                min_chapters: minChapters,
                limit: LIMIT,
                page,
                author: search || undefined,
            })

            const computedTotalPages = data.total_pages != null
                ? data.total_pages
                : ((data.results || []).length < LIMIT ? page : page + 1)

            if (computedTotalPages > 0 && page > computedTotalPages) {
                updatePage(computedTotalPages, 'replace')
                return
            }

            setResults(data.results || [])
            setTotalPages(computedTotalPages)
        } catch {
            setResults([])
        }

        setLoading(false)
    }, [category, genreInclude, genreExclude, status, sortBy, hasCompletionData, minChapters, page, search, updatePage])

    useEffect(() => { loadManga() }, [loadManga])

    // ── Prefetch next page in regular mode ──
    useEffect(() => {
        if (!loading && !category && page < totalPages) {
            fetchManga({
                genre_include: genreInclude.length > 0 ? genreInclude : undefined,
                genre_exclude: genreExclude.length > 0 ? genreExclude : undefined,
                status,
                sort_by: sortBy,
                has_completion_data: hasCompletionData,
                min_chapters: minChapters,
                limit: LIMIT,
                page: page + 1,
                author: search || undefined,
            }).catch(() => { })
        }
    }, [category, page, totalPages, loading, genreInclude, genreExclude, status, sortBy, hasCompletionData, minChapters, search])

    const handleQuickFilter = (nextCategory) => {
        if (nextCategory === category) {
            applyURL({ ...DEFAULT_FILTERS }, 'push')
            return
        }
        updateCategory(nextCategory)
    }

    const handleSearchChange = (v) => {
        setSearchInput(v)
        updateMainFilters({ search: v.trim() }, 'replace')
    }

    const handleSearchKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault()
            commitSearch()
        }
    }

    const handleMinChaptersChange = (v) => {
        setMinChaptersInput(v)
        updateMainFilters({ min_chapters: toNonNegativeInt(v, 0) }, 'replace')
    }

    const handleMinChaptersKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault()
            commitMinChapters()
        }
    }

    // ── Build page number array with ellipsis ──
    const getPageNumbers = () => {
        const pages = []
        const last = totalPages
        if (last <= 7) {
            for (let i = 1; i <= last; i++) pages.push(i)
            return pages
        }
        pages.push(1)
        if (page > 3) pages.push('...')
        const start = Math.max(2, page - 1)
        const end = Math.min(last - 1, page + 1)
        for (let i = start; i <= end; i++) pages.push(i)
        if (page < last - 2) pages.push('...')
        if (last > 1) pages.push(last)
        return pages
    }

    return (
        <>
            <header className={`site-header ${isHeaderHidden ? 'site-header-hidden' : ''}`}>
                <div className="header-left">
                    <Link to="/" className="logo" onClick={() => updateMainFilters({}, 'push')}>
                        <span className="logo-manhwa">MANHWA</span>
                        <span className="logo-rank">RANK</span>
                    </Link>
                </div>
                
                <div className="header-center">
                    <div className="nav-tabs">
                        <span className={`nav-tab ${topTab === 'browse' && category==='' ? 'active' : ''}`} onClick={() => { setTopTab('browse'); handleQuickFilter('') }}>ALL</span>
                        <span className={`nav-tab ${topTab === 'browse' && category==='manhwa' ? 'active' : ''}`} onClick={() => { setTopTab('browse'); handleQuickFilter('manhwa') }}>MANHWA</span>
                        <span className={`nav-tab ${topTab === 'browse' && category==='manhua' ? 'active' : ''}`} onClick={() => { setTopTab('browse'); handleQuickFilter('manhua') }}>MANHUA</span>
                        <span className={`nav-tab ${topTab === 'charts' ? 'active' : ''}`} onClick={() => setTopTab('charts')}>CHARTS</span>
                        <span className={`nav-tab ${topTab === 'watchlist' ? 'active' : ''}`} onClick={() => setTopTab('watchlist')}>WATCHLIST</span>
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
                    <button className="theme-toggle" onClick={toggleTheme}>
                        {isDark ? '○ LIGHT' : '● DARK'}
                    </button>
                </div>
            </header>

            {topTab === 'browse' && (
                <>
                    <div className="category-strip">
                        {QUICK_FILTERS.map(({ label, category: quickCategory }) => (
                            <div
                                key={quickCategory}
                                className={`category-card ${activeQuickFilter === quickCategory ? 'active' : ''}`}
                                data-cat={quickCategory}
                                onClick={() => handleQuickFilter(quickCategory)}
                            >
                                <div className="cat-name">{label.replace(/[^a-zA-Z\s]/g, '').trim()}</div>
                                <div className="cat-count">VIEW CATEGORY</div>
                            </div>
                        ))}
                    </div>

                    <div className="mobile-filter-toolbar">
                        <button
                            type="button"
                            className="mobile-filter-btn"
                            onClick={() => setIsMobileFilterOpen(true)}
                        >
                            FILTER
                            {activeFilterCount > 0 && <span className="mobile-filter-badge">{activeFilterCount}</span>}
                        </button>
                        <div className="mobile-view-toggle">
                            <button
                                type="button"
                                className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                                onClick={() => setViewMode('list')}
                            >
                                LIST
                            </button>
                            <button
                                type="button"
                                className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
                                onClick={() => setViewMode('grid')}
                            >
                                GRID
                            </button>
                        </div>
                    </div>

                    {isMobileFilterOpen && <div className="mobile-filter-backdrop" onClick={() => setIsMobileFilterOpen(false)} />}

                    <div className="main-layout">
                {/* ── Filter Panel ── */}
                <aside className={`filter-panel ${isMobileFilterOpen ? 'mobile-open' : ''}`}>
                    <div className="mobile-filter-header">
                        <span>Filters</span>
                        <button type="button" onClick={() => setIsMobileFilterOpen(false)}>Close</button>
                    </div>
                    <UnifiedGenrePicker
                        allGenres={genres}
                        defaultExcludedGenres={defaultExcludedGenres}
                        include={genreInclude}
                        manualExclude={manualGenreExclude}
                        onToggleState={(g) => {
                            if (genreInclude.includes(g)) {
                                if (manualGenreExclude.length >= MAX_EXCLUDE_GENRES) return;
                                updateMainFilters({
                                    genre_include: genreInclude.filter(x => x !== g),
                                    genre_exclude: [...manualGenreExclude, g],
                                    exclude_mode: 'custom'
                                })
                            } else if (manualGenreExclude.includes(g)) {
                                updateMainFilters({
                                    genre_exclude: manualGenreExclude.filter(x => x !== g),
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
                    />

                    <div className="filter-section">
                        <div className="filter-label">Status</div>
                        <div className="filter-status-segmented mobile-only">
                            {['', 'ongoing', 'completed'].map((v) => (
                                <button
                                    type="button"
                                    key={`seg-${v || 'all'}`}
                                    className={`filter-segment ${status === v ? 'active' : ''}`}
                                    onClick={() => updateMainFilters({ status: v })}
                                >
                                    {v === '' ? 'ALL' : v}
                                </button>
                            ))}
                        </div>

                        <div className="desktop-only">
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
                        <div className="filter-label filter-label-row">
                            <span>Min Chapters</span>
                            <span className="mobile-value-badge mobile-only">{minChapters}</span>
                        </div>
                        <input
                            className="mobile-range-slider mobile-only"
                            type="range"
                            min="0"
                            max="500"
                            step="10"
                            value={minChapters}
                            onChange={(e) => handleMinChaptersChange(e.target.value)}
                        />
                        <input
                            className="filter-number desktop-only"
                            type="number"
                            min="0"
                            value={minChaptersInput}
                            onFocus={() => { minCommitBaseRef.current = minChapters }}
                            onChange={(e) => handleMinChaptersChange(e.target.value)}
                            onBlur={commitMinChapters}
                            onKeyDown={handleMinChaptersKeyDown}
                        />
                    </div>

                    <button
                        type="button"
                        className="mobile-apply-btn"
                        onClick={() => setIsMobileFilterOpen(false)}
                    >
                        APPLY FILTERS
                    </button>
                </aside>

                {/* ── Main Content ── */}
                <main className="content-area" onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}>
                    <div className="view-controls" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px', gap: '8px' }}>
                        <button 
                            className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                            onClick={() => setViewMode('list')}
                        >
                            LIST VIEW
                        </button>
                        <button 
                            className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
                            onClick={() => setViewMode('grid')}
                        >
                            GRID VIEW
                        </button>
                    </div>

                    {loading && (
                        <div className={viewMode === 'list' ? 'manga-list' : 'manga-grid'}>
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
                            <div className={viewMode === 'list' ? 'manga-list' : 'manga-grid'}>
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
                                            <div className="strip-watchlist-col"><WatchlistButton manga={m} compact /></div>
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
            )}

            {topTab === 'charts' && (
                <div className="main-layout">
                    <main className="content-area">
                        <GenreUniverseSection
                            onBrowseGenres={(nextGenres) => {
                                setTopTab('browse')
                                updateMainFilters({
                                    genre_include: nextGenres,
                                    genre_exclude: [],
                                    exclude_mode: 'custom',
                                })
                            }}
                        />
                    </main>
                </div>
            )}

            {topTab === 'watchlist' && (
                <div className="main-layout">
                    <main className="content-area">
                        <WatchlistSection />
                    </main>
                </div>
            )}
        </>
    )
}

export default function App() {
    return (
        <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/watchlist" element={<HomePage initialTopTab="watchlist" />} />
            <Route path="/manga/:title" element={<MangaDetailPage />} />
        </Routes>
    )
}




