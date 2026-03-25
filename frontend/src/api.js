export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchManga({ genre_include, genre_exclude, author, min_chapters, status, sort_by, has_completion_data, limit, page }) {
    const params = new URLSearchParams();
    if (genre_include) genre_include.forEach(g => params.append('genre_include', g));
    if (genre_exclude) genre_exclude.forEach(g => params.append('genre_exclude', g));
    if (author) params.set('author', author);
    if (min_chapters > 0) params.set('min_chapters', min_chapters);
    if (status) params.set('status', status);
    if (sort_by) params.set('sort_by', sort_by);
    if (has_completion_data) params.set('has_completion_data', 'true');
    if (limit) params.set('limit', limit);
    if (page) params.set('page', page);
    const res = await fetch(`${API_BASE}/manga?${params}`);
    if (!res.ok) throw new Error('Failed to fetch manga');
    return res.json();
}

export async function fetchMangaByTitle(title) {
    const res = await fetch(`${API_BASE}/manga/${encodeURIComponent(title)}`);
    if (!res.ok) throw new Error('Manga not found');
    return res.json();
}

export async function fetchGenres() {
    const res = await fetch(`${API_BASE}/genres`);
    if (!res.ok) throw new Error('Failed to fetch genres');
    const data = await res.json();
    return data.genres;
}

export async function fetchBlacklistedGenres() {
    const res = await fetch(`${API_BASE}/genres/blacklist`);
    if (!res.ok) throw new Error('Failed to fetch blacklisted genres');
    const data = await res.json();
    return data.blacklist || [];
}

export async function fetchTopCategory(category) {
    const res = await fetch(`${API_BASE}/top/${encodeURIComponent(category)}`);
    if (!res.ok) throw new Error('Failed to fetch top category');
    const data = await res.json();
    return data.results;
}

export async function fetchGenreRelationships() {
    const res = await fetch(`${API_BASE}/genres/relationships`);
    if (!res.ok) throw new Error('Failed to fetch genre relationships');
    return res.json();
}

export async function fetchStats() {
    const res = await fetch(`${API_BASE}/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
}

function getAdminHeaders(adminPassword) {
    return {
        'X-Admin-Password': adminPassword,
    };
}

async function fetchAdminJSON(path, adminPassword) {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: getAdminHeaders(adminPassword),
    });

    if (!res.ok) {
        let detail = '';

        try {
            const payload = await res.clone().json();
            if (payload && typeof payload === 'object' && payload.detail) {
                detail = String(payload.detail).trim();
            } else if (typeof payload === 'string') {
                detail = payload.trim();
            }
        } catch {
            // Ignore JSON parse errors and fall back to plain text.
        }

        if (!detail) {
            try {
                detail = (await res.text()).trim();
            } catch {
                // Ignore text read errors and keep empty detail.
            }
        }

        const defaults = {
            401: 'Unauthorized. Re-enter admin password.',
            404: 'Admin endpoint not found. Restart backend on latest code.',
            502: 'Upstream data source failed.',
            503: 'Admin endpoints are not configured. Set ADMIN_PASSWORD and restart backend.',
        };

        const message = detail || defaults[res.status] || 'Failed to fetch admin data.';
        const err = new Error(message);
        err.status = res.status;
        err.detail = detail || message;
        throw err;
    }

    return res.json();
}

export function fetchAdminStats(adminPassword) {
    return fetchAdminJSON('/admin/stats', adminPassword);
}

export function fetchAdminSourceHealth(adminPassword) {
    return fetchAdminJSON('/admin/source-health', adminPassword);
}

export function fetchAdminScoreDistribution(adminPassword) {
    return fetchAdminJSON('/admin/score-distribution', adminPassword);
}

export function fetchAdminCoverage(adminPassword) {
    return fetchAdminJSON('/admin/coverage', adminPassword);
}

function buildAnalyticsQuery(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            query.set(key, String(value));
        }
    });
    return query.toString();
}

export function fetchAdminAnalyticsSearches(adminPassword, { days = 30, limit = 20 } = {}) {
    const qs = buildAnalyticsQuery({ days, limit });
    return fetchAdminJSON(`/admin/analytics/searches${qs ? `?${qs}` : ''}`, adminPassword);
}

export function fetchAdminAnalyticsMangaViews(adminPassword, { days = 30, limit = 20 } = {}) {
    const qs = buildAnalyticsQuery({ days, limit });
    return fetchAdminJSON(`/admin/analytics/manga-views${qs ? `?${qs}` : ''}`, adminPassword);
}

export function fetchAdminAnalyticsFilters(adminPassword, { days = 30, limit = 15 } = {}) {
    const qs = buildAnalyticsQuery({ days, limit });
    return fetchAdminJSON(`/admin/analytics/filters${qs ? `?${qs}` : ''}`, adminPassword);
}

export function fetchAdminAnalyticsWatchlist(adminPassword, { days = 30 } = {}) {
    const qs = buildAnalyticsQuery({ days });
    return fetchAdminJSON(`/admin/analytics/watchlist${qs ? `?${qs}` : ''}`, adminPassword);
}

export function fetchAdminAnalyticsUsers(adminPassword) {
    return fetchAdminJSON(`/admin/analytics/users`, adminPassword);
}

// ── Module-level cache for similar manga (survives route navigation) ──
const _similarCache = new Map();

export async function fetchSimilarManga(title, { bypassCache = false } = {}) {
    if (!bypassCache && _similarCache.has(title)) {
        return _similarCache.get(title);
    }
    const res = await fetch(
        `${API_BASE}/similar-manga/${encodeURIComponent(title)}`
    );
    if (!res.ok) throw new Error('Failed to fetch similar manga');
    const data = await res.json();
    const results = data.results || [];
    _similarCache.set(title, results);
    return results;
}
