import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useTheme } from './hooks/useTheme.js'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'

import { Routes, Route, Link, useLocation, useSearchParams } from 'react-router-dom'
import { fetchManga, fetchGenres, fetchBlacklistedGenres, fetchTopCategory, submitFeedback } from './api'
import { useAnalytics } from './hooks/useAnalytics.js'
import MangaDetailPage from './MangaDetailPage.jsx'
import AdminPage from './pages/AdminPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import GenreUniverseSection from './components/charts/GenreUniverseSection.jsx'
import { WatchlistSection } from './components/WatchlistSection.jsx'
import { MangaCard, MangaCardSkeleton } from './components/MangaCard.jsx'
import { AuthButton } from './components/AuthButton.jsx'
import Footer from './components/Footer.jsx'
import NotFound from './pages/NotFound.jsx'
import Privacy from './pages/Privacy.jsx'
import Terms from './pages/Terms.jsx'


const QUICK_FILTERS = [
    { label: '⭐ Masterpieces', category: 'masterpieces', apiCategory: 'completion-masterpieces', desc: 'High quality manga (40+ chapters, 5k+ views) that most readers finish.' },
    { label: '⚠️ Hard to Finish', category: 'hard-to-finish', apiCategory: 'completion-traps', desc: 'Highly rated manga (40+ chapters, 5k+ views) that most readers drop.' },
    { label: '🍿 Guilty Pleasures', category: 'guilty-pleasures', desc: 'Lower-rated manga (40+ chapters, 5k+ views) that readers keep finishing anyway.' },
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

const TOUR_STORAGE_KEY = 'manhwarank-tour-completed'
const FEEDBACK_NOTICE_DURATION_MS = 2600

const DEFAULT_FEEDBACK_FORM = {
    feedback_type: 'general',
    message: '',
    email: '',
    website: '',
}

const TOUR_STEPS_DESKTOP = [
    {
        key: 'score-trust',
        selector: '[data-tour="score-trust"]',
        copy: 'Scores blend AniList, MAL, MangaDex, and Kitsu so one source cannot dominate the ranking.',
    },
    {
        key: 'category-strip',
        selector: '[data-tour="category-strip"]',
        copy: 'These top strips are behavioral lanes like Masterpieces and Hard to Finish, not simple genres.',
    },
    {
        key: 'genre-mix',
        selector: '[data-tour="genre-picker"]',
        copy: 'Genre toggles are tri-state: include, exclude, or neutral so you can shape very precise lists.',
    },
    {
        key: 'charts-map',
        selector: '[data-tour="charts-tab"]',
        copy: 'Open CHARTS anytime to explore the live genre-relationship map and jump back into browse filters.',
    },
]

const TOUR_STEPS_MOBILE = [
    {
        key: 'score-trust',
        selector: '[data-tour="score-trust"]',
        copy: 'Scores blend AniList, MAL, MangaDex, and Kitsu so one source cannot dominate the ranking.',
    },
    {
        key: 'category-strip',
        selector: '[data-tour="category-strip"]',
        copy: 'These top strips are behavioral lanes like Masterpieces and Hard to Finish, not simple genres.',
    },
    {
        key: 'mobile-filter',
        selector: '[data-tour="mobile-filter-btn"]',
        copy: 'Tap FILTER, then tap a genre to include it and tap again to move it into exclude mode.',
    },
    {
        key: 'charts-map',
        selector: '[data-tour="charts-tab"]',
        copy: 'Open CHARTS anytime to explore the live genre-relationship map and jump back into browse filters.',
    },
]

function AppLogo({ isDark, onClick }) {
    const [hasError, setHasError] = useState(false)
    const src = isDark ? '/logo-dark.svg' : '/logo-light.svg'
    const alt = isDark ? 'ManhwaRank dark logo' : 'ManhwaRank light logo'

    return (
        <Link to="/" className="flex items-center" aria-label="Go to homepage" onClick={onClick}>
            {hasError ? (
                <span className="flex items-center font-serif text-xl font-bold text-text-primary sm:text-[22px] md:text-[24px] lg:text-[26px]">
                    MANHWA<span className="font-mono text-accent-red">RANK</span>
                </span>
            ) : (
                <img
                    src={src}
                    alt={alt}
                    className="block h-auto w-full object-contain"
                    style={{ width: 'clamp(170px, 24vw, 220px)', maxWidth: '220px' }}
                    onError={() => setHasError(true)}
                />
            )}
        </Link>
    )
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

function findVisibleTourTarget(selector) {
    const candidates = Array.from(document.querySelectorAll(selector))

    for (const node of candidates) {
        const rect = node.getBoundingClientRect()
        if (rect.width <= 0 || rect.height <= 0) continue

        const style = window.getComputedStyle(node)
        if (style.display === 'none' || style.visibility === 'hidden') continue

        return node
    }

    return null
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
        <div className="filter-section border-b border-border/80 py-2.5" data-tour="genre-picker">
            <div className="filter-header-row mb-2 flex items-center justify-between">
                <div className="filter-label mb-0 font-mono text-[11px] uppercase tracking-[0.12em] text-text-primary/80">Genres</div>
                {hasActiveFilters && (
                    <button
                        type="button"
                        className="clear-all-link font-mono text-[10px] uppercase tracking-[0.1em] text-accent-red"
                        onClick={onClearAll}
                    >
                        Clear all
                    </button>
                )}
            </div>

            {hasActiveFilters && (
                <div className="genres-summary mb-2 space-y-1">
                    {include.length > 0 && (
                        <div className="genres-summary-line flex flex-wrap items-center gap-1.5">
                            <span className="genres-summary-label font-mono text-[10px] uppercase tracking-[0.08em] text-text-ghost">Include:</span>
                            {include.map(g => (
                                <button
                                    key={g}
                                    type="button"
                                    className="summary-tag include rounded border border-accent-gold/40 px-1.5 py-0.5 text-[10px] text-accent-gold"
                                    onClick={() => onToggleState(g)}
                                >
                                    {g} <span className="remove">×</span>
                                </button>
                            ))}
                        </div>
                    )}
                    {manualExclude.length > 0 && (
                        <div className="genres-summary-line flex flex-wrap items-center gap-1.5">
                            <span className="genres-summary-label font-mono text-[10px] uppercase tracking-[0.08em] text-text-ghost">Exclude:</span>
                            {manualExclude.map(g => (
                                <button
                                    key={g}
                                    type="button"
                                    className="summary-tag exclude rounded border border-accent-red/40 px-1.5 py-0.5 text-[10px] text-accent-red"
                                    onClick={() => onToggleState(g)}
                                >
                                    {g} <span className="remove">×</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}

            <button
                type="button"
                className="genre-grid-toggle flex h-10 w-full items-center justify-between border border-border/90 bg-surface px-3 font-mono text-[11px] uppercase tracking-[0.12em] text-text-primary/85"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                {isExpanded ? 'Hide Genres' : 'Show All Genres'}
                <span aria-hidden="true">{isExpanded ? '▲' : '▼'}</span>
            </button>

            {isExpanded && (
                <div className="genre-grid-container mt-2">
                    <input
                        className="genre-grid-search h-9 w-full border border-border/90 bg-surface px-3 text-xs text-text-primary placeholder:text-text-ghost"
                        placeholder="Filter genres..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <div className="genre-grid mt-2 grid max-h-[34vh] grid-cols-2 gap-1.5 overflow-y-auto pr-1 md:max-h-[46vh] md:grid-cols-1 lg:grid-cols-2">
                        {filteredGenres.map(g => {
                            let stateClass = 'neutral'
                            let prefix = ''
                            if (includeSet.has(g)) {
                                stateClass = 'include'
                                prefix = '+ '
                            } else if (manualExcludeSet.has(g)) {
                                stateClass = 'exclude'
                                prefix = '− '
                            } else if (defaultExcludeSet.has(g)) {
                                stateClass = 'default-exclude'
                                prefix = '− '
                            }

                            const chipTone =
                                stateClass === 'include'
                                    ? 'border-accent-gold/45 text-accent-gold bg-accent-gold/5'
                                    : stateClass === 'exclude'
                                        ? 'border-accent-red/45 text-accent-red bg-accent-red/5'
                                        : stateClass === 'default-exclude'
                                            ? 'border-border text-text-ghost bg-background'
                                            : 'border-border text-text-secondary bg-surface'

                            return (
                                <button
                                    key={g}
                                    type="button"
                                    className={`genre-chip min-h-10 rounded border px-2 py-1 text-left text-[11px] leading-tight ${chipTone}`}
                                    onClick={() => onToggleState(g)}
                                    title={stateClass === 'default-exclude' ? 'Excluded by default (click to include)' : ''}
                                >
                                    {prefix}{g}
                                </button>
                            )
                        })}
                    </div>
                    <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.08em] text-text-secondary/80">
                        Include max: {maxInclude} • Exclude max: {maxExclude}
                    </div>
                </div>
            )}
        </div>
    )
}
function HomePage({ initialTopTab = 'browse' }) {
    const location = useLocation()
    const [searchParams, setSearchParams] = useSearchParams()
    const { theme, toggleTheme, isDark } = useTheme()
    const { track } = useAnalytics()
    const [topTab, setTopTab] = useState(initialTopTab)
    const [isHeaderHidden, setIsHeaderHidden] = useState(false)

    const [comingSoonHint, setComingSoonHint] = useState(null)
    const [isFeedbackOpen, setIsFeedbackOpen] = useState(false)
    const [feedbackForm, setFeedbackForm] = useState(DEFAULT_FEEDBACK_FORM)
    const [feedbackStatus, setFeedbackStatus] = useState('idle')
    const [feedbackError, setFeedbackError] = useState('')
    const [feedbackNotice, setFeedbackNotice] = useState('')

    const [viewportWidth, setViewportWidth] = useState(
        typeof window !== 'undefined' ? window.innerWidth : 1280,
    )
    const [tourMode, setTourMode] = useState('idle')
    const [tourStepIndex, setTourStepIndex] = useState(0)
    const [tourTargetRect, setTourTargetRect] = useState(null)

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
    const [categoryTooltip, setCategoryTooltip] = useState(null)
    const reduceMotion = useReducedMotion()

    const searchCommitBaseRef = useRef('')
    const minCommitBaseRef = useRef(0)
    const copyTimeoutRef = useRef(null)
    const filterTrackReadyRef = useRef(false)
    const lastScrollYRef = useRef(0)
    const scrollFrameRef = useRef(null)
    const comingSoonTimeoutRef = useRef(null)
    const comingSoonRef = useRef(null)
    const feedbackLayerRef = useRef(null)
    const feedbackNoticeTimeoutRef = useRef(null)

    const isFirstVisitRoute = location.pathname === '/'
    const isTourActive = tourMode === 'active'
    const isTourPromptVisible = tourMode === 'prompt'
    const isMobileViewport = viewportWidth < 1024
    const tourSteps = useMemo(
        () => (isMobileViewport ? TOUR_STEPS_MOBILE : TOUR_STEPS_DESKTOP),
        [isMobileViewport],
    )

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

        if (committed.length > 0) {
            track(
                'search',
                { metadata: { query: committed.toLowerCase() } },
                {
                    persist: true,
                },
            )
        }

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

    const resetFeedbackForm = useCallback(() => {
        setFeedbackForm({ ...DEFAULT_FEEDBACK_FORM })
    }, [])

    const closeFeedbackPanel = useCallback(() => {
        setIsFeedbackOpen(false)
        setFeedbackStatus('idle')
        setFeedbackError('')
        resetFeedbackForm()
    }, [resetFeedbackForm])

    const toggleFeedbackPanel = useCallback(() => {
        if (isTourActive) return

        if (isFeedbackOpen) {
            closeFeedbackPanel()
            return
        }

        setComingSoonHint(null)
        setFeedbackStatus('idle')
        setFeedbackError('')
        setIsFeedbackOpen(true)
    }, [isTourActive, isFeedbackOpen, closeFeedbackPanel])

    const showComingSoon = useCallback((label, event) => {
        if (isTourActive) return

        closeFeedbackPanel()

        const rect = event.currentTarget.getBoundingClientRect()
        setComingSoonHint({
            message: `${label} is coming soon`,
            left: rect.left + (rect.width / 2),
            top: rect.bottom + 12,
        })
    }, [isTourActive, closeFeedbackPanel])

    const handleFeedbackSubmit = useCallback(async (event) => {
        event.preventDefault()
        if (feedbackStatus === 'sending') return

        const trimmedMessage = feedbackForm.message.trim()
        if (!trimmedMessage) {
            setFeedbackError('Please write a message before sending.')
            return
        }

        setFeedbackStatus('sending')
        setFeedbackError('')

        try {
            await submitFeedback({
                feedback_type: feedbackForm.feedback_type,
                message: trimmedMessage,
                email: feedbackForm.email.trim() || null,
                page: `${location.pathname}${location.search}`,
                website: feedbackForm.website,
            })

            track('feedback_submit', {
                metadata: {
                    type: feedbackForm.feedback_type,
                },
            })

            closeFeedbackPanel()
            setFeedbackNotice('Feedback received. Thank you.')
        } catch (err) {
            const message = err?.message || 'Could not send feedback right now. Please try again shortly.'
            setFeedbackStatus('error')
            setFeedbackError(message)
        }
    }, [feedbackForm, feedbackStatus, location.pathname, location.search, closeFeedbackPanel, track])

    const markTourCompleted = useCallback(() => {
        try {
            window.localStorage.setItem(TOUR_STORAGE_KEY, 'true')
        } catch {
            // Ignore localStorage write failures.
        }
        setTourMode('idle')
        setTourStepIndex(0)
        setTourTargetRect(null)
    }, [])

    const handleTourSkip = useCallback(() => {
        markTourCompleted()
    }, [markTourCompleted])

    const handleTourStart = useCallback(() => {
        setTopTab('browse')
        setIsMobileFilterOpen(false)
        setComingSoonHint(null)
        closeFeedbackPanel()
        setTourStepIndex(0)
        setTourMode('active')
    }, [closeFeedbackPanel])

    const handleTourNext = useCallback(() => {
        if (tourStepIndex >= tourSteps.length - 1) {
            markTourCompleted()
            return
        }
        setTourStepIndex((prev) => prev + 1)
    }, [tourStepIndex, tourSteps.length, markTourCompleted])

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
        const onResize = () => setViewportWidth(window.innerWidth)
        window.addEventListener('resize', onResize)
        return () => window.removeEventListener('resize', onResize)
    }, [])

    useEffect(() => {
        if (!isFirstVisitRoute) {
            setTourMode('idle')
            return
        }

        let hasCompletedTour = false
        try {
            hasCompletedTour = window.localStorage.getItem(TOUR_STORAGE_KEY) === 'true'
        } catch {
            hasCompletedTour = false
        }

        if (hasCompletedTour) {
            setTourMode('idle')
            return
        }

        setTourMode((current) => (current === 'active' ? current : 'prompt'))
    }, [isFirstVisitRoute])

    useEffect(() => {
        if (!isTourActive) return
        if (tourStepIndex < tourSteps.length) return
        setTourStepIndex(0)
    }, [isTourActive, tourStepIndex, tourSteps.length])

    useEffect(() => {
        if (!isTourActive) {
            setTourTargetRect(null)
            return
        }

        const step = tourSteps[tourStepIndex]
        if (!step) {
            setTourTargetRect(null)
            return
        }

        const updateTargetRect = () => {
            const target = findVisibleTourTarget(step.selector)
            if (!target) {
                setTourTargetRect(null)
                return
            }

            const rect = target.getBoundingClientRect()
            setTourTargetRect({
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
                bottom: rect.bottom,
            })
        }

        const target = findVisibleTourTarget(step.selector)
        if (target) {
            target.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' })
        }

        updateTargetRect()
        window.addEventListener('resize', updateTargetRect)
        window.addEventListener('scroll', updateTargetRect, true)

        return () => {
            window.removeEventListener('resize', updateTargetRect)
            window.removeEventListener('scroll', updateTargetRect, true)
        }
    }, [isTourActive, tourStepIndex, tourSteps, reduceMotion, topTab, isMobileFilterOpen, loading])

    useEffect(() => {
        if (!comingSoonHint) return

        if (comingSoonTimeoutRef.current) {
            clearTimeout(comingSoonTimeoutRef.current)
        }

        comingSoonTimeoutRef.current = setTimeout(() => {
            setComingSoonHint(null)
        }, 2200)

        return () => {
            if (comingSoonTimeoutRef.current) {
                clearTimeout(comingSoonTimeoutRef.current)
                comingSoonTimeoutRef.current = null
            }
        }
    }, [comingSoonHint])

    useEffect(() => {
        if (!comingSoonHint) return

        const onPointerDown = (event) => {
            const target = event.target instanceof Element ? event.target : null
            if (!target) return
            if (comingSoonRef.current?.contains(target)) return
            if (target.closest('[data-coming-soon-trigger="true"]')) return
            setComingSoonHint(null)
        }

        document.addEventListener('pointerdown', onPointerDown)
        return () => document.removeEventListener('pointerdown', onPointerDown)
    }, [comingSoonHint])

    useEffect(() => {
        if (!isFeedbackOpen) return

        const onPointerDown = (event) => {
            const target = event.target instanceof Element ? event.target : null
            if (!target) return
            if (feedbackLayerRef.current?.contains(target)) return
            closeFeedbackPanel()
        }

        document.addEventListener('pointerdown', onPointerDown)
        return () => document.removeEventListener('pointerdown', onPointerDown)
    }, [isFeedbackOpen, closeFeedbackPanel])

    useEffect(() => {
        if (!feedbackNotice) return

        if (feedbackNoticeTimeoutRef.current) {
            clearTimeout(feedbackNoticeTimeoutRef.current)
        }

        feedbackNoticeTimeoutRef.current = setTimeout(() => {
            setFeedbackNotice('')
        }, FEEDBACK_NOTICE_DURATION_MS)

        return () => {
            if (feedbackNoticeTimeoutRef.current) {
                clearTimeout(feedbackNoticeTimeoutRef.current)
                feedbackNoticeTimeoutRef.current = null
            }
        }
    }, [feedbackNotice])

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

    useEffect(() => {
        if (!filterTrackReadyRef.current) {
            filterTrackReadyRef.current = true
            return
        }

        if (isCategoryMode) return

        track(
            'filter_applied',
            {
                filter_state: {
                    genre_include: genreInclude,
                    genre_exclude: genreExclude,
                    status: status || 'all',
                    sort_by: sortBy,
                    min_chapters: minChapters,
                    search: search || '',
                },
            },
            {
                persist: true,
            },
        )
    }, [genreInclude, genreExclude, status, sortBy, minChapters, search, isCategoryMode, track])

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
        const hasActiveFilters =
            genreInclude.length > 0 ||
            genreExclude.length > 0 ||
            Boolean(status) ||
            minChapters > 0 ||
            Boolean(search)

        if (!loading && !category && !hasActiveFilters && page > 1 && page < totalPages) {
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

        if (nextCategory) {
            track(
                'category_view',
                {
                    category: nextCategory,
                },
                {
                    persist: false,
                },
            )
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

    const activeTourStep = isTourActive ? tourSteps[tourStepIndex] : null

    const tourTooltipStyle = useMemo(() => {
        const viewportHeight = typeof window !== 'undefined' ? window.innerHeight : 900
        const cardWidth = Math.min(340, viewportWidth - 32)

        if (!tourTargetRect) {
            return {
                width: `${cardWidth}px`,
                left: '50%',
                top: '50%',
                transform: 'translate(-50%, -50%)',
            }
        }

        const margin = 16
        const minHalf = (cardWidth / 2) + margin
        const maxHalf = viewportWidth - minHalf
        const preferredLeft = tourTargetRect.left + (tourTargetRect.width / 2)
        const left = Math.max(minHalf, Math.min(preferredLeft, maxHalf))

        const estimatedHeight = 176
        let top = tourTargetRect.bottom + 14
        if (top + estimatedHeight > viewportHeight - margin) {
            top = Math.max(margin, tourTargetRect.top - estimatedHeight - 14)
        }

        return {
            width: `${cardWidth}px`,
            left: `${left}px`,
            top: `${top}px`,
            transform: 'translateX(-50%)',
        }
    }, [tourTargetRect, viewportWidth])

    const tourSpotlightStyle = useMemo(() => {
        if (!tourTargetRect) return null

        const pad = 8
        return {
            left: `${Math.max(6, tourTargetRect.left - pad)}px`,
            top: `${Math.max(6, tourTargetRect.top - pad)}px`,
            width: `${tourTargetRect.width + (pad * 2)}px`,
            height: `${tourTargetRect.height + (pad * 2)}px`,
        }
    }, [tourTargetRect])

    const filterPanelInner = (
        <>
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

            <div className="filter-section border-b border-border/80 py-2.5">
                <div className="filter-label mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-text-primary/80">Status</div>
                <div className="grid grid-cols-3 gap-1.5 lg:hidden">
                    {['', 'ongoing', 'completed'].map((v) => (
                        <button
                            type="button"
                            key={`seg-${v || 'all'}`}
                            className={`filter-segment min-h-11 border border-border px-2 py-2 font-mono text-[11px] tracking-[0.08em] ${status === v ? 'active bg-background text-text-primary' : 'text-text-secondary'}`}
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
                            className={`filter-status-option cursor-pointer font-mono text-xs tracking-[0.08em] ${status === v ? 'active text-text-primary' : 'text-text-secondary'}`}
                            onClick={() => updateMainFilters({ status: v })}
                        >
                            {v === '' ? 'ALL' : v}
                        </span>
                    ))}
                </div>
            </div>

            <div className="filter-section border-b border-border/80 py-2.5">
                <div className="filter-label mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-text-primary/80">Sort By</div>
                <select className="filter-select h-10 w-full border border-border/90 bg-surface px-3 text-sm text-text-primary" value={sortBy} onChange={(e) => updateMainFilters({ sort_by: e.target.value })}>
                    <option value="score">Best Score</option>
                    <option value="views">Most Popular</option>
                    <option value="chapters">Most Chapters</option>
                    <option value="completion">Completion Rate</option>
                </select>
            </div>

            <div className="filter-section py-2.5" style={{ borderBottom: 'none' }}>
                <div className="filter-label filter-label-row mb-2 flex items-center justify-between font-mono text-[11px] uppercase tracking-[0.12em] text-text-primary/80">
                    <span>Min Chapters</span>
                    <span className="mobile-value-badge rounded bg-background px-2 py-0.5 text-[10px] text-text-primary lg:hidden">{minChapters}</span>
                </div>
                <input
                    className="mobile-range-slider w-full accent-[#C1121F] lg:hidden"
                    type="range"
                    min="0"
                    max="500"
                    step="10"
                    value={minChapters}
                    onChange={(e) => handleMinChaptersChange(e.target.value)}
                />
                <input
                    className="filter-number hidden h-10 w-full border border-border/90 bg-surface px-3 py-2 text-sm text-text-primary lg:block"
                    type="number"
                    min="0"
                    value={minChaptersInput}
                    onFocus={() => { minCommitBaseRef.current = minChapters }}
                    onChange={(e) => handleMinChaptersChange(e.target.value)}
                    onBlur={commitMinChapters}
                    onKeyDown={handleMinChaptersKeyDown}
                />
            </div>

            <div className="sticky bottom-0 z-10 mt-3 border-t border-border bg-elevated pt-3 lg:hidden">
                <button
                    type="button"
                    className="mobile-apply-btn inline-flex h-11 w-full items-center justify-center border border-accent-red bg-accent-red font-mono text-xs tracking-[0.12em] text-white"
                    onClick={() => setIsMobileFilterOpen(false)}
                >
                    APPLY FILTERS
                </button>
            </div>
        </>
    )

    return (
        <>
            <header
                className={[
                    'sticky top-0 z-[100] border-b border-border bg-background/85 backdrop-blur-md',
                    'transition-transform duration-200',
                    isHeaderHidden ? '-translate-y-full opacity-0 pointer-events-none' : 'translate-y-0 opacity-100',
                ].join(' ')}
            >
                <div className="px-3 py-2 sm:px-6 md:flex md:h-14 md:items-center md:justify-between md:gap-3 md:py-0">
                    <div className="flex items-center justify-between gap-2">
                        <div className="shrink-0" data-tour="score-trust">
                            <AppLogo isDark={isDark} onClick={() => updateMainFilters({}, 'push')} />
                        </div>

                        <div className="flex items-center gap-1.5 md:hidden">
                            <AuthButton />
                            <button
                                className="min-h-11 border border-border bg-surface px-2.5 py-1.5 font-mono text-[11px] tracking-[0.08em] text-text-secondary transition-colors hover:text-text-primary"
                                onClick={toggleTheme}
                            >
                                {isDark ? '○ LIGHT' : '● DARK'}
                            </button>
                        </div>
                    </div>

                    <div className="hidden h-full items-center gap-6 md:flex">
                        <button
                            type="button"
                            className={`h-full border-b-2 px-0 font-mono text-[11px] tracking-[0.15em] transition-colors ${topTab === 'browse' && category === '' ? 'border-accent-red text-text-primary' : 'border-transparent text-text-secondary hover:text-text-primary'}`}
                            onClick={() => { setTopTab('browse'); handleQuickFilter('') }}
                        >
                            ALL
                        </button>
                        <button
                            type="button"
                            data-coming-soon-trigger="true"
                            className="coming-soon-nav h-full border-b-2 border-transparent px-0 font-mono text-[11px] tracking-[0.15em] text-text-secondary transition-colors hover:text-text-primary"
                            onClick={(event) => showComingSoon('MANHWA', event)}
                        >
                            MANHWA
                        </button>
                        <button
                            type="button"
                            data-coming-soon-trigger="true"
                            className="coming-soon-nav h-full border-b-2 border-transparent px-0 font-mono text-[11px] tracking-[0.15em] text-text-secondary transition-colors hover:text-text-primary"
                            onClick={(event) => showComingSoon('MANHUA', event)}
                        >
                            MANHUA
                        </button>
                        <button
                            type="button"
                            data-tour="charts-tab"
                            className={`h-full border-b-2 px-0 font-mono text-[11px] tracking-[0.15em] transition-colors ${topTab === 'charts' ? 'border-accent-red text-text-primary' : 'border-transparent text-text-secondary hover:text-text-primary'}`}
                            onClick={() => setTopTab('charts')}
                        >
                            CHARTS
                        </button>
                        <button
                            type="button"
                            className={`h-full border-b-2 px-0 font-mono text-[11px] tracking-[0.15em] transition-colors ${topTab === 'watchlist' ? 'border-accent-red text-text-primary' : 'border-transparent text-text-secondary hover:text-text-primary'}`}
                            onClick={() => setTopTab('watchlist')}
                        >
                            WATCHLIST
                        </button>
                    </div>

                    <div className="mt-2 flex items-center gap-2 md:mt-0 md:ml-auto" ref={feedbackLayerRef}>
                        <div className="relative w-full md:w-[230px] lg:w-[290px]">
                            <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-text-secondary/70">
                                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 fill-none stroke-current stroke-[1.8]">
                                    <circle cx="11" cy="11" r="6.5" />
                                    <path d="m16 16 4 4" strokeLinecap="round" />
                                </svg>
                            </span>
                            <input
                                className="h-11 w-full border border-border bg-surface px-3 py-1.5 pl-9 text-sm text-text-primary outline-none transition-colors placeholder:text-text-secondary focus:border-accent-red md:h-9 md:text-xs"
                                type="text"
                                placeholder="Search titles..."
                                value={searchInput}
                                onFocus={() => { searchCommitBaseRef.current = search }}
                                onChange={(e) => handleSearchChange(e.target.value)}
                                onBlur={commitSearch}
                                onKeyDown={handleSearchKeyDown}
                            />
                        </div>
                        <button
                            type="button"
                            className="feedback-trigger h-11 min-w-[74px] border border-border bg-surface px-2.5 py-0 font-mono text-[10px] tracking-[0.12em] text-text-secondary transition-colors hover:text-text-primary disabled:opacity-45 md:h-9 md:min-w-[96px]"
                            onClick={toggleFeedbackPanel}
                            disabled={isTourActive}
                            title={isTourActive ? 'Finish or skip the tour first' : 'Send feedback'}
                        >
                            <span className="md:hidden">FEED</span>
                            <span className="hidden md:inline">FEEDBACK</span>
                        </button>

                        <div className="hidden items-center gap-2 md:flex [&_.auth-btn--signin]:ml-0 [&_.auth-btn--signin]:h-9 [&_.auth-btn--signin]:px-2.5 [&_.auth-btn--signin]:py-0 [&_.auth-user-menu]:ml-0 [&_.auth-avatar-btn]:h-9 [&_.auth-avatar-btn]:w-9">
                            <AuthButton />
                            <button
                                className="h-9 min-w-[92px] border border-border bg-surface px-2.5 py-0 font-mono text-[11px] tracking-[0.08em] text-text-secondary transition-colors hover:text-text-primary"
                                onClick={toggleTheme}
                            >
                                {isDark ? '○ LIGHT' : '● DARK'}
                            </button>
                        </div>

                        {isFeedbackOpen && (
                            <div className="feedback-panel absolute right-0 top-[calc(100%+10px)] z-[140] w-[min(420px,calc(100vw-24px))] border border-border bg-elevated p-3 shadow-2xl md:p-4" role="dialog" aria-label="Send feedback">
                                <form className="space-y-3" onSubmit={handleFeedbackSubmit}>
                                    <div className="feedback-panel-head flex items-center justify-between gap-3">
                                        <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-text-primary">Send feedback</span>
                                        <button type="button" className="font-mono text-[10px] uppercase tracking-[0.12em] text-text-secondary hover:text-text-primary" onClick={closeFeedbackPanel}>
                                            Close
                                        </button>
                                    </div>

                                    <label className="feedback-label block font-mono text-[10px] uppercase tracking-[0.11em] text-text-secondary">
                                        Type
                                        <select
                                            className="feedback-input mt-1 h-10 w-full border border-border bg-surface px-3 text-xs text-text-primary outline-none"
                                            value={feedbackForm.feedback_type}
                                            onChange={(e) => setFeedbackForm((prev) => ({ ...prev, feedback_type: e.target.value }))}
                                        >
                                            <option value="bug">Bug report</option>
                                            <option value="suggestion">Suggestion</option>
                                            <option value="general">General</option>
                                        </select>
                                    </label>

                                    <label className="feedback-label block font-mono text-[10px] uppercase tracking-[0.11em] text-text-secondary">
                                        Message
                                        <textarea
                                            rows={4}
                                            maxLength={2000}
                                            className="feedback-input mt-1 w-full resize-y border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none placeholder:text-text-secondary"
                                            placeholder="What should we improve first?"
                                            value={feedbackForm.message}
                                            onChange={(e) => setFeedbackForm((prev) => ({ ...prev, message: e.target.value }))}
                                        />
                                    </label>

                                    <label className="feedback-label block font-mono text-[10px] uppercase tracking-[0.11em] text-text-secondary">
                                        Email (optional)
                                        <input
                                            type="email"
                                            maxLength={200}
                                            className="feedback-input mt-1 h-10 w-full border border-border bg-surface px-3 text-sm text-text-primary outline-none placeholder:text-text-secondary"
                                            placeholder="your@email.com (if you'd like a reply)"
                                            value={feedbackForm.email}
                                            onChange={(e) => setFeedbackForm((prev) => ({ ...prev, email: e.target.value }))}
                                        />
                                    </label>

                                    <input
                                        type="text"
                                        tabIndex={-1}
                                        autoComplete="off"
                                        className="hidden"
                                        value={feedbackForm.website}
                                        onChange={(e) => setFeedbackForm((prev) => ({ ...prev, website: e.target.value }))}
                                        aria-hidden="true"
                                    />

                                    {feedbackError && (
                                        <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-accent-red">{feedbackError}</p>
                                    )}

                                    <p className="font-mono text-[10px] text-text-ghost">
                                        Optional email is only used if we need to reply.
                                    </p>

                                    <div className="flex items-center justify-end gap-2">
                                        <button
                                            type="button"
                                            className="h-9 border border-border bg-surface px-3 font-mono text-[10px] uppercase tracking-[0.12em] text-text-secondary"
                                            onClick={closeFeedbackPanel}
                                            disabled={feedbackStatus === 'sending'}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="submit"
                                            className="h-9 border border-accent-red bg-accent-red px-3 font-mono text-[10px] uppercase tracking-[0.12em] text-white disabled:opacity-60"
                                            disabled={feedbackStatus === 'sending'}
                                        >
                                            {feedbackStatus === 'sending' ? 'Sending…' : 'Send'}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        )}
                    </div>
                </div>
            </header>

            {comingSoonHint && (
                <div
                    ref={comingSoonRef}
                    className="coming-soon-tooltip fixed z-[145] border border-border bg-elevated px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-text-primary"
                    style={{
                        left: `${comingSoonHint.left}px`,
                        top: `${comingSoonHint.top}px`,
                        transform: 'translateX(-50%)',
                    }}
                    role="status"
                    aria-live="polite"
                >
                    {comingSoonHint.message}
                </div>
            )}

            {feedbackNotice && (
                <div className="feedback-notice fixed left-1/2 top-[74px] z-[150] -translate-x-1/2 border border-border bg-elevated px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-text-primary" role="status" aria-live="polite">
                    {feedbackNotice}
                </div>
            )}

            {isFirstVisitRoute && isTourPromptVisible && (
                <div className="tour-optin fixed bottom-4 left-4 z-[155] w-[min(360px,calc(100vw-24px))] border border-border bg-elevated p-3 shadow-2xl md:p-4" role="dialog" aria-label="Quick guide">
                    <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-text-primary">First time here?</p>
                    <p className="mt-2 text-sm text-text-secondary">Take a 60-second walkthrough or explore on your own.</p>
                    <div className="mt-3 flex items-center justify-end gap-2">
                        <button type="button" className="h-9 border border-border bg-surface px-3 font-mono text-[10px] uppercase tracking-[0.12em] text-text-secondary" onClick={handleTourSkip}>
                            Skip
                        </button>
                        <button type="button" className="h-9 border border-accent-red bg-accent-red px-3 font-mono text-[10px] uppercase tracking-[0.12em] text-white" onClick={handleTourStart}>
                            Quick tour
                        </button>
                    </div>
                </div>
            )}

            {isTourActive && activeTourStep && (
                <div className="tour-layer fixed inset-0 z-[160]" onClick={handleTourNext}>
                    <div className="tour-layer-dim absolute inset-0" />
                    {tourSpotlightStyle && (
                        <div
                            className="tour-spotlight absolute border border-accent-red/80"
                            style={tourSpotlightStyle}
                            aria-hidden="true"
                        />
                    )}

                    <div
                        className="tour-card absolute border border-border bg-elevated p-3 shadow-2xl md:p-4"
                        style={tourTooltipStyle}
                        onClick={(event) => event.stopPropagation()}
                        role="dialog"
                        aria-label="Tour step"
                    >
                        <div className="mb-2 flex items-center justify-between gap-3 font-mono text-[10px] uppercase tracking-[0.12em] text-text-ghost">
                            <span>Step {tourStepIndex + 1}/{tourSteps.length}</span>
                            <button type="button" className="text-text-secondary hover:text-text-primary" onClick={handleTourSkip}>
                                Skip
                            </button>
                        </div>

                        <p className="text-sm leading-6 text-text-primary">{activeTourStep.copy}</p>

                        <div className="mt-3 flex items-center justify-end gap-2">
                            <button
                                type="button"
                                className="h-9 border border-accent-red bg-accent-red px-3 font-mono text-[10px] uppercase tracking-[0.12em] text-white"
                                onClick={handleTourNext}
                            >
                                {tourStepIndex >= tourSteps.length - 1 ? 'Done' : 'Next'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {topTab === 'browse' && (
                <>
                    <div className="relative border-b border-border">
                        <div className="category-strip flex gap-3 overflow-x-auto px-3 py-3.5 md:px-6 md:py-4" data-tour="category-strip">
                            {QUICK_FILTERS.map(({ label, category: quickCategory, desc }) => (
                                <div
                                    key={quickCategory}
                                    className={`category-card group relative min-w-[176px] cursor-pointer overflow-hidden border border-border/70 border-l-4 px-4 py-2.5 transition-all duration-200 ${activeQuickFilter === quickCategory ? 'border-accent-red/55 bg-elevated shadow-[inset_0_1px_0_rgba(193,18,31,0.35)]' : 'bg-surface text-text-primary hover:-translate-y-0.5 hover:border-accent-red/35 hover:bg-elevated/90'}`}
                                    data-cat={quickCategory}
                                    onClick={() => handleQuickFilter(quickCategory)}
                                    onMouseEnter={(e) => {
                                        if (!desc) return
                                        const rect = e.currentTarget.getBoundingClientRect()
                                        setCategoryTooltip({
                                            text: desc,
                                            left: rect.left + (rect.width / 2),
                                            top: rect.top - 10,
                                        })
                                    }}
                                    onMouseLeave={() => setCategoryTooltip(null)}
                                >
                                    <span
                                        className={`pointer-events-none absolute inset-x-0 top-0 h-px transition-opacity ${activeQuickFilter === quickCategory ? 'bg-gradient-to-r from-transparent via-accent-red/80 to-transparent opacity-100' : 'bg-gradient-to-r from-transparent via-text-primary/25 to-transparent opacity-0 group-hover:opacity-100'}`}
                                    />
                                    <div className={`cat-name font-mono text-xs uppercase tracking-[0.12em] ${activeQuickFilter === quickCategory ? 'text-text-primary' : 'text-text-primary/90 group-hover:text-text-primary'}`}>{label.replace(/[^a-zA-Z\s]/g, '').trim()}</div>
                                </div>
                            ))}
                        </div>
                        <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-14 bg-gradient-to-l from-background via-background/82 to-transparent md:block" />
                    </div>

                    {categoryTooltip && (
                        <div
                            className="category-tooltip"
                            style={{
                                left: `${categoryTooltip.left}px`,
                                top: `${categoryTooltip.top}px`,
                            }}
                        >
                            {categoryTooltip.text}
                        </div>
                    )}

                    <div className="mobile-filter-toolbar sticky top-[88px] z-40 flex items-center justify-between gap-2 border-b border-border bg-background/95 px-3 py-2 backdrop-blur-sm md:top-14 lg:hidden">
                        <button
                            type="button"
                            data-tour="mobile-filter-btn"
                            className="mobile-filter-btn relative inline-flex h-11 items-center justify-center gap-2 border border-accent-red bg-elevated px-3 font-mono text-xs tracking-[0.12em] text-text-primary"
                            onClick={() => setIsMobileFilterOpen(true)}
                        >
                            FILTER
                            {activeFilterCount > 0 && <span className="mobile-filter-badge inline-flex min-w-5 items-center justify-center rounded-full bg-accent-red px-1.5 py-0.5 text-[10px] text-white">{activeFilterCount}</span>}
                        </button>
                        <div className="mobile-view-toggle inline-flex items-center border border-border bg-surface">
                            <button
                                type="button"
                                className={`view-toggle-btn h-11 px-3 font-mono text-[11px] tracking-[0.12em] ${viewMode === 'list' ? 'active border-r border-border bg-elevated text-text-primary' : 'border-r border-border text-text-secondary'}`}
                                onClick={() => setViewMode('list')}
                            >
                                LIST
                            </button>
                            <button
                                type="button"
                                className={`view-toggle-btn h-11 px-3 font-mono text-[11px] tracking-[0.12em] ${viewMode === 'grid' ? 'active bg-elevated text-text-primary' : 'text-text-secondary'}`}
                                onClick={() => setViewMode('grid')}
                            >
                                GRID
                            </button>
                        </div>
                    </div>

                    <AnimatePresence>
                        {isMobileFilterOpen && (
                            <motion.div
                                className="mobile-filter-backdrop fixed inset-0 z-40 bg-black/55 lg:hidden"
                                onClick={() => setIsMobileFilterOpen(false)}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: reduceMotion ? 0 : 0.18 }}
                            />
                        )}
                    </AnimatePresence>

                    <div className="main-layout relative mx-auto flex w-full max-w-[1600px] gap-4 px-3 py-3 md:px-6 md:py-6">
                        {/* ── Filter Panel ── */}
                        <AnimatePresence>
                            {isMobileFilterOpen && (
                                <motion.aside
                                    className="filter-panel fixed inset-x-0 bottom-0 z-50 max-h-[82vh] w-full rounded-t-2xl border border-border border-b-0 bg-elevated p-4 shadow-2xl lg:hidden"
                                    initial={{ y: '100%' }}
                                    animate={{ y: '0%' }}
                                    exit={{ y: '100%' }}
                                    transition={{ type: reduceMotion ? 'tween' : 'spring', duration: reduceMotion ? 0 : 0.22, bounce: 0.12 }}
                                >
                                    <div className="mobile-filter-header mb-2 border-b border-border pb-3">
                                        <div className="mx-auto mb-3 h-1.5 w-12 rounded-full bg-border" />
                                        <div className="flex items-center justify-between font-mono text-xs uppercase tracking-[0.14em] text-text-secondary">
                                            <span>Filters</span>
                                            <button type="button" className="text-text-primary" onClick={() => setIsMobileFilterOpen(false)}>Close</button>
                                        </div>
                                    </div>
                                    <div className="max-h-[66vh] space-y-0 overflow-y-auto">
                                        {filterPanelInner}
                                    </div>
                                </motion.aside>
                            )}
                        </AnimatePresence>

                        <aside className="filter-panel hidden w-full border border-border bg-elevated p-3.5 lg:sticky lg:top-[76px] lg:block lg:max-h-[calc(100vh-96px)] lg:max-w-[320px] lg:overflow-y-auto">
                            {filterPanelInner}
                        </aside>

                        {/* ── Main Content ── */}
                        <main className="content-area min-w-0 flex-1 pb-20 lg:pb-0" onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}>
                            <div className="view-controls mb-4 hidden justify-end gap-2 lg:flex">
                                <button
                                    className={`view-toggle-btn h-10 border border-border px-3 font-mono text-xs tracking-[0.12em] ${viewMode === 'list' ? 'active bg-elevated text-text-primary' : 'bg-surface text-text-secondary'}`}
                                    onClick={() => setViewMode('list')}
                                >
                                    LIST VIEW
                                </button>
                                <button
                                    className={`view-toggle-btn h-10 border border-border px-3 font-mono text-xs tracking-[0.12em] ${viewMode === 'grid' ? 'active bg-elevated text-text-primary' : 'bg-surface text-text-secondary'}`}
                                    onClick={() => setViewMode('grid')}
                                >
                                    GRID VIEW
                                </button>
                            </div>

                            {loading && (
                                <div className={viewMode === 'list' ? 'space-y-3' : 'grid grid-cols-3 gap-1.5 sm:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7'}>
                                    {Array.from({ length: 8 }).map((_, i) => (
                                        <MangaCardSkeleton key={i} viewMode={viewMode} />
                                    ))}
                                </div>
                            )}

                            {!loading && results.length === 0 && (
                                <div className="px-6 py-12 text-center font-mono text-sm tracking-[0.08em] text-text-secondary">
                                    NO RESULTS FOUND.
                                </div>
                            )}

                            {!loading && results.length > 0 && (
                                <>
                                    <div className={viewMode === 'list' ? 'space-y-3' : 'grid grid-cols-3 gap-1.5 sm:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7'}>
                                        {results.map((m, i) => {
                                            const rank = (page - 1) * LIMIT + i + 1;
                                            const handleCardClick = () => {
                                                track(
                                                    'manga_click',
                                                    {
                                                        manga_title: m.title,
                                                        metadata: {
                                                            score: m.aggregated_score ?? null,
                                                            rank,
                                                        },
                                                    },
                                                    {
                                                        persist: true,
                                                    },
                                                )
                                            }
                                            return (
                                                <MangaCard
                                                    key={`${m.title}-${i}`}
                                                    manga={m}
                                                    rank={rank}
                                                    viewMode={viewMode}
                                                    onTrackClick={handleCardClick}
                                                />
                                            )
                                        })}
                                    </div>

                                    {!activeQuickFilter && totalPages > 1 && (
                                        <div className="mt-5 flex items-center justify-center gap-1.5">
                                            <button
                                                className="h-9 border border-border bg-surface px-3 font-mono text-xs tracking-[0.1em] text-text-secondary disabled:opacity-40"
                                                disabled={page <= 1}
                                                onClick={() => updatePage(page - 1)}
                                            >
                                                PREV
                                            </button>
                                            {getPageNumbers().map((p, i) =>
                                                p === '...' ? (
                                                    <span key={`e${i}`} className="px-2 text-text-ghost">…</span>
                                                ) : (
                                                    <span
                                                        key={p}
                                                        className={`inline-flex h-9 min-w-9 cursor-pointer items-center justify-center border px-2 font-mono text-xs ${p === page ? 'border-accent-red bg-elevated text-text-primary' : 'border-border bg-surface text-text-secondary'}`}
                                                        onClick={() => updatePage(p)}
                                                    >
                                                        {p}
                                                    </span>
                                                )
                                            )}
                                            <button
                                                className="h-9 border border-border bg-surface px-3 font-mono text-xs tracking-[0.1em] text-text-secondary disabled:opacity-40"
                                                disabled={page >= totalPages}
                                                onClick={() => updatePage(Math.min(totalPages, page + 1))}
                                            >
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
                <div className="main-layout relative mx-auto flex w-full max-w-[1600px] gap-4 px-3 py-3 md:px-6 md:py-6">
                    <main className="content-area min-w-0 flex-1 pb-20 lg:pb-0">
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
                <div className="main-layout relative mx-auto flex w-full max-w-[1600px] gap-4 px-3 py-3 md:px-6 md:py-6">
                    <main className="content-area min-w-0 flex-1 pb-20 lg:pb-0">
                        <WatchlistSection />
                    </main>
                </div>
            )}

            <nav
                className="mobile-bottom-nav fixed inset-x-0 bottom-0 z-[90] border-t border-border bg-background/95 px-3 pt-2 backdrop-blur-md lg:hidden"
                style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 8px)' }}
            >
                <div className="mx-auto grid max-w-[560px] grid-cols-3 gap-2">
                    <button
                        type="button"
                        className={`min-h-11 border px-2 font-mono text-[11px] tracking-[0.1em] ${topTab === 'browse' ? 'border-accent-red bg-elevated text-text-primary' : 'border-border bg-surface text-text-secondary'}`}
                        onClick={() => setTopTab('browse')}
                    >
                        BROWSE
                    </button>
                    <button
                        type="button"
                        data-tour="charts-tab"
                        className={`min-h-11 border px-2 font-mono text-[11px] tracking-[0.1em] ${topTab === 'charts' ? 'border-accent-red bg-elevated text-text-primary' : 'border-border bg-surface text-text-secondary'}`}
                        onClick={() => setTopTab('charts')}
                    >
                        CHARTS
                    </button>
                    <button
                        type="button"
                        className={`min-h-11 border px-2 font-mono text-[11px] tracking-[0.1em] ${topTab === 'watchlist' ? 'border-accent-red bg-elevated text-text-primary' : 'border-border bg-surface text-text-secondary'}`}
                        onClick={() => setTopTab('watchlist')}
                    >
                        WATCHLIST
                    </button>
                </div>
            </nav>
        </>
    )
}

export default function App() {
    return (
        <div className="flex min-h-screen flex-col">
            <div className="flex flex-1 flex-col">
                <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/watchlist" element={<HomePage initialTopTab="watchlist" />} />
                    <Route path="/manga/:title" element={<MangaDetailPage />} />
                    <Route path="/admin" element={<AdminPage />} />
                    <Route path="/profile" element={<ProfilePage />} />
                    <Route path="/privacy" element={<Privacy />} />
                    <Route path="/terms" element={<Terms />} />
                    <Route path="*" element={<NotFound />} />
                </Routes>
            </div>
            <Footer />
        </div>
    )
}




