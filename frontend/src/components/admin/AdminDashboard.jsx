import { useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import {
    fetchAdminCoverage,
    fetchAdminAnalyticsFilters,
    fetchAdminAnalyticsMangaViews,
    fetchAdminAnalyticsSearches,
    fetchAdminAnalyticsWatchlist,
    fetchAdminAnalyticsUsers,
    fetchAdminScoreDistribution,
    fetchAdminSourceHealth,
    fetchAdminStats,
} from '../../api.js';

function statusForScoreRate(rate) {
    if (rate >= 80) return 'good';
    if (rate >= 60) return 'warn';
    return 'bad';
}

function statusForUnscored(unscored) {
    if (unscored < 5000) return 'good';
    if (unscored < 9000) return 'warn';
    return 'bad';
}

function statusForDays(daysSinceUpdate) {
    if (daysSinceUpdate <= 3) return 'good';
    if (daysSinceUpdate <= 7) return 'warn';
    return 'bad';
}

function statusForTotal(total) {
    if (total >= 20000) return 'good';
    if (total >= 15000) return 'warn';
    return 'bad';
}

function statusLabel(status) {
    if (status === 'warn') return 'WATCH';
    if (status === 'bad') return 'ALERT';
    return 'HEALTHY';
}

function KPICard({ label, value, unit, status, sublabel }) {
    return (
        <div className={`admin-kpi admin-kpi-${status}`}>
            <div className="admin-kpi-label">{label}</div>
            <div className="admin-kpi-value-wrap">
                <div className="admin-kpi-value">{value}</div>
                {unit ? <div className="admin-kpi-unit">{unit}</div> : null}
            </div>
            <div className="admin-kpi-foot">
                <span className={`admin-status admin-status-${status}`}>{statusLabel(status)}</span>
                {sublabel ? <span className="admin-kpi-sub">{sublabel}</span> : null}
            </div>
        </div>
    );
}

function NullRateBar({ pct }) {
    const status = pct < 40 ? 'good' : pct < 70 ? 'warn' : 'bad';
    return (
        <div className="admin-rate-wrap">
            <div className="admin-rate-track">
                <div className={`admin-rate-fill admin-rate-fill-${status}`} style={{ width: `${pct}%` }} />
            </div>
            <span className={`admin-rate-text admin-rate-text-${status}`}>{pct}%</span>
        </div>
    );
}

function SourceHealthTable({ sources }) {
    return (
        <div className="admin-panel">
            <div className="admin-panel-title">Source Health</div>
            <div className="admin-table-wrap">
                <table className="admin-table">
                    <thead>
                        <tr>
                            <th>Source</th>
                            <th>Records</th>
                            <th>Null Rating %</th>
                            <th>Null Views %</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sources.map((source) => {
                            const status = source.null_rating_pct < 40 ? 'good' : source.null_rating_pct < 70 ? 'warn' : 'bad';
                            return (
                                <tr key={source.source}>
                                    <td className="admin-source-name">{source.source}</td>
                                    <td>{source.total_records.toLocaleString()}</td>
                                    <td><NullRateBar pct={source.null_rating_pct} /></td>
                                    <td><NullRateBar pct={source.null_views_pct} /></td>
                                    <td><span className={`admin-status admin-status-${status}`}>{statusLabel(status)}</span></td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function ScoreDistributionChart({ data }) {
    const max = Math.max(...data.map((entry) => entry.count), 1);

    return (
        <div className="admin-panel admin-panel-tight">
            <div className="admin-panel-title">Score Distribution</div>
            <div className="admin-bars">
                {data.map((entry) => {
                    const height = Math.max(12, (entry.count / max) * 100);
                    return (
                        <div key={entry.range} className="admin-bar-col" title={`${entry.range}: ${entry.count.toLocaleString()} manga`}>
                            <div className="admin-bar-track">
                                <div className="admin-bar-fill" style={{ height: `${height}%` }} />
                            </div>
                            <div className="admin-bar-range">{entry.range}</div>
                            <div className="admin-bar-value">{entry.count.toLocaleString()}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function SourceCoverageBar({ data }) {
    const total = data.reduce((sum, item) => sum + item.manga_count, 0);

    return (
        <div className="admin-panel">
            <div className="admin-panel-title">Source Coverage</div>
            <div className="admin-coverage-track">
                {data.map((item) => {
                    const widthPct = total ? (item.manga_count / total) * 100 : 0;
                    const levelClass = item.sources <= 1 ? 'bad' : item.sources === 2 ? 'warn' : item.sources === 3 ? 'good' : 'max';
                    return (
                        <div
                            key={item.sources}
                            className={`admin-coverage-segment admin-coverage-${levelClass}`}
                            style={{ width: `${widthPct}%` }}
                            title={`${item.sources} sources: ${item.manga_count.toLocaleString()} manga`}
                        />
                    );
                })}
            </div>
            <div className="admin-coverage-legend">
                {data.map((item) => {
                    const levelClass = item.sources <= 1 ? 'bad' : item.sources === 2 ? 'warn' : item.sources === 3 ? 'good' : 'max';
                    const pct = total ? Math.round((item.manga_count / total) * 100) : 0;
                    return (
                        <div key={item.sources} className="admin-coverage-item">
                            <span className={`admin-coverage-dot admin-coverage-${levelClass}`} />
                            <span>{item.sources} source{item.sources > 1 ? 's' : ''}</span>
                            <strong>{item.manga_count.toLocaleString()}</strong>
                            <span className="admin-muted">({pct}%)</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function WidgetHeader({ title, period }) {
    return (
        <div className="admin-widget-header">
            <div className="admin-panel-title admin-panel-title-inline">{title}</div>
            {period ? <div className="admin-muted">{period}</div> : null}
        </div>
    );
}

function TopSearchesWidget({ data }) {
    const max = Math.max(...data.map((item) => item.count), 1);
    return (
        <div className="admin-panel admin-panel-padded">
            <WidgetHeader title="Top Searched Titles" period="Last 30 days" />
            <div className="admin-rank-list">
                {data.slice(0, 10).map((item, idx) => (
                    <div className="admin-rank-row" key={`${item.query}-${idx}`}>
                        <div className="admin-rank-label">{idx + 1}. {item.query}</div>
                        <div className="admin-rank-meter">
                            <div className="admin-rank-fill" style={{ width: `${(item.count / max) * 100}%` }} />
                        </div>
                        <div className="admin-rank-value">{item.count}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function MostViewedWidget({ data }) {
    return (
        <div className="admin-panel admin-panel-padded">
            <WidgetHeader title="Most Viewed Manga" period="Last 30 days" />
            <div className="admin-rank-list">
                {data.slice(0, 10).map((item, idx) => (
                    <div className="admin-rank-row" key={`${item.title}-${idx}`}>
                        <div className="admin-rank-label">{idx + 1}. {item.title}</div>
                        <div className="admin-rank-value">{item.views}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function PopularFiltersWidget({ data }) {
    return (
        <div className="admin-panel admin-panel-padded">
            <WidgetHeader title="Popular Filters" period="Last 30 days" />
            <div className="admin-tag-cloud">
                {data.slice(0, 15).map((item) => (
                    <div className="admin-filter-tag" key={item.combination}>
                        <span>{item.combination}</span>
                        <strong>{item.count}</strong>
                    </div>
                ))}
            </div>
        </div>
    );
}

function WatchlistWidget({ data }) {
    const daily = data?.daily || [];
    const topAdded = data?.top_added || [];
    const max = Math.max(...daily.map((item) => item.adds + item.removes), 1);

    return (
        <div className="admin-panel admin-panel-padded">
            <WidgetHeader title="Watchlist Activity" period="Last 30 days" />
            <div className="admin-mini-bars">
                {daily.slice(-14).map((item) => {
                    const total = item.adds + item.removes;
                    return (
                        <div className="admin-mini-bar-col" key={item.date}>
                            <div className="admin-mini-bar-track" title={`${item.date}: +${item.adds} / -${item.removes}`}>
                                <div className="admin-mini-bar-add" style={{ height: `${(item.adds / max) * 100}%` }} />
                                <div className="admin-mini-bar-remove" style={{ height: `${(item.removes / max) * 100}%` }} />
                            </div>
                            <div className="admin-mini-bar-label">{item.date.slice(5)}</div>
                            <div className="admin-mini-bar-total">{total}</div>
                        </div>
                    );
                })}
            </div>

            {topAdded.length > 0 ? (
                <div className="admin-top-added">
                    <div className="admin-panel-title admin-panel-title-inline">Most Added</div>
                    {topAdded.slice(0, 5).map((item, idx) => (
                        <div className="admin-rank-row" key={`${item.title}-${idx}`}>
                            <div className="admin-rank-label">{idx + 1}. {item.title}</div>
                            <div className="admin-rank-value">+{item.count}</div>
                        </div>
                    ))}
                </div>
            ) : null}
        </div>
    );
}

function UserAnalyticsWidget({ data }) {
    if (!data) return null;
    return (
        <div className="admin-panel admin-panel-padded">
            <WidgetHeader title="Active Users" period="Registered + Anonymous" />
            <div className="admin-grid-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '16px', marginTop: '12px' }}>
                <div className="admin-kpi admin-kpi-good" style={{ padding: '12px' }}>
                    <div className="admin-kpi-label">DAU (1d)</div>
                    <div className="admin-kpi-value-wrap">
                        <div className="admin-kpi-value" style={{ fontSize: '1.5rem' }}>{data.dau.total.toLocaleString()}</div>
                    </div>
                    <div className="admin-kpi-foot" style={{ marginTop: '4px' }}>
                        <span className="admin-muted">{data.dau.registered} reg, {data.dau.anonymous} anon</span>
                    </div>
                </div>
                <div className="admin-kpi admin-kpi-good" style={{ padding: '12px' }}>
                    <div className="admin-kpi-label">WAU (7d)</div>
                    <div className="admin-kpi-value-wrap">
                        <div className="admin-kpi-value" style={{ fontSize: '1.5rem' }}>{data.wau.total.toLocaleString()}</div>
                    </div>
                    <div className="admin-kpi-foot" style={{ marginTop: '4px' }}>
                        <span className="admin-muted">{data.wau.registered} reg, {data.wau.anonymous} anon</span>
                    </div>
                </div>
                <div className="admin-kpi admin-kpi-good" style={{ padding: '12px' }}>
                    <div className="admin-kpi-label">MAU (30d)</div>
                    <div className="admin-kpi-value-wrap">
                        <div className="admin-kpi-value" style={{ fontSize: '1.5rem' }}>{data.mau.total.toLocaleString()}</div>
                    </div>
                    <div className="admin-kpi-foot" style={{ marginTop: '4px' }}>
                        <span className="admin-muted">{data.mau.registered} reg, {data.mau.anonymous} anon</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

function UmamiWidget() {
    const shareUrl = import.meta.env.VITE_UMAMI_SHARE_URL || '';
    if (!shareUrl) {
        return (
            <div className="admin-panel admin-panel-padded">
                <WidgetHeader title="Traffic Overview (Umami)" period="Configure VITE_UMAMI_SHARE_URL" />
                <div className="admin-muted">Set VITE_UMAMI_SHARE_URL in frontend env to enable embed.</div>
            </div>
        );
    }

    return (
        <div className="admin-panel admin-panel-padded">
            <WidgetHeader title="Traffic Overview (Umami)" period="Passive analytics" />
            <iframe
                src={shareUrl}
                className="admin-umami-frame"
                title="Umami Analytics"
            />
        </div>
    );
}

function PanelError({ message }) {
    return <div className="admin-widget-error">{message}</div>;
}

function formatWidgetError(reason, fallbackLabel) {
    const status = reason?.status;
    const detail = typeof reason?.detail === 'string' ? reason.detail.trim() : '';
    const message = typeof reason?.message === 'string' ? reason.message.trim() : '';
    const base = detail || message || fallbackLabel;
    return status ? `${base} (HTTP ${status})` : base;
}

function QuickActions() {
    const actions = [
        {
            label: 'Enrichment Plan',
            desc: 'Run targeted enrichment playbook',
            href: '/UNSCORED_MANGA_PLAN.md',
        },
        {
            label: 'Supabase Dashboard',
            desc: 'Inspect db rows and query plans',
            href: 'https://supabase.com/dashboard',
        },
        {
            label: 'Render Logs',
            desc: 'Monitor backend deploy and runtime',
            href: 'https://dashboard.render.com',
        },
    ];

    return (
        <div className="admin-quick-actions">
            {actions.map((action) => (
                <a key={action.label} href={action.href} target="_blank" rel="noreferrer" className="admin-quick-action">
                    <div className="admin-quick-label">{action.label}</div>
                    <div className="admin-quick-desc">{action.desc}</div>
                </a>
            ))}
        </div>
    );
}

export default function AdminDashboard({ adminPassword, onLogout }) {
    const [stats, setStats] = useState(null);
    const [sourceHealth, setSourceHealth] = useState(null);
    const [scoreDist, setScoreDist] = useState(null);
    const [coverage, setCoverage] = useState(null);
    const [topSearches, setTopSearches] = useState(null);
    const [mostViewed, setMostViewed] = useState(null);
    const [popularFilters, setPopularFilters] = useState(null);
    const [watchlistData, setWatchlistData] = useState(null);
    const [usersData, setUsersData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [lastFetch, setLastFetch] = useState(null);
    const [errors, setErrors] = useState({});

    const loadAll = async ({ silent = false } = {}) => {
        if (silent) {
            setRefreshing(true);
        } else {
            setLoading(true);
        }

        const calls = [
            fetchAdminStats(adminPassword),
            fetchAdminSourceHealth(adminPassword),
            fetchAdminScoreDistribution(adminPassword),
            fetchAdminCoverage(adminPassword),
            fetchAdminAnalyticsSearches(adminPassword),
            fetchAdminAnalyticsMangaViews(adminPassword),
            fetchAdminAnalyticsFilters(adminPassword),
            fetchAdminAnalyticsWatchlist(adminPassword),
            fetchAdminAnalyticsUsers(adminPassword),
        ];

        const [
            statsRes,
            sourceRes,
            distRes,
            coverageRes,
            searchRes,
            viewedRes,
            filtersRes,
            watchlistRes,
            usersRes,
        ] = await Promise.allSettled(calls);
        const nextErrors = {};

        if (statsRes.status === 'fulfilled') {
            setStats(statsRes.value);
        } else {
            let statsMessage = formatWidgetError(statsRes.reason, 'Failed to load admin stats.');
            if (statsRes.reason?.status === 401) {
                statsMessage = `${statsMessage} Use Log Out, then enter password again.`;
            }
            nextErrors.stats = statsMessage;
        }

        if (sourceRes.status === 'fulfilled') {
            setSourceHealth(sourceRes.value);
        } else {
            nextErrors.source = formatWidgetError(sourceRes.reason, 'Source health is unavailable right now.');
        }

        if (distRes.status === 'fulfilled') {
            setScoreDist(distRes.value);
        } else {
            nextErrors.distribution = formatWidgetError(distRes.reason, 'Score distribution failed to load.');
        }

        if (coverageRes.status === 'fulfilled') {
            setCoverage(coverageRes.value);
        } else {
            nextErrors.coverage = formatWidgetError(coverageRes.reason, 'Coverage data could not be loaded.');
        }

        if (searchRes.status === 'fulfilled') {
            setTopSearches(searchRes.value || []);
        } else {
            nextErrors.top_searches = formatWidgetError(searchRes.reason, 'Top searches are unavailable right now.');
        }

        if (viewedRes.status === 'fulfilled') {
            setMostViewed(viewedRes.value || []);
        } else {
            nextErrors.most_viewed = formatWidgetError(viewedRes.reason, 'Most viewed manga is unavailable right now.');
        }

        if (filtersRes.status === 'fulfilled') {
            setPopularFilters(filtersRes.value || []);
        } else {
            nextErrors.popular_filters = formatWidgetError(filtersRes.reason, 'Popular filter combinations are unavailable right now.');
        }

        if (watchlistRes.status === 'fulfilled') {
            setWatchlistData(watchlistRes.value || { daily: [], top_added: [] });
        } else {
            nextErrors.watchlist = formatWidgetError(watchlistRes.reason, 'Watchlist analytics are unavailable right now.');
        }

        if (usersRes.status === 'fulfilled') {
            setUsersData(usersRes.value);
        } else {
            nextErrors.users = formatWidgetError(usersRes.reason, 'Active users metrics unavailable right now.');
        }

        setErrors(nextErrors);
        setLastFetch(new Date());
        setLoading(false);
        setRefreshing(false);
    };

    useEffect(() => {
        loadAll();
    }, []);

    const daysSinceUpdate = useMemo(() => {
        if (!stats?.last_updated) return null;
        return Math.max(0, Math.floor((Date.now() - new Date(stats.last_updated).getTime()) / 86400000));
    }, [stats]);

    const headerStatus = useMemo(() => {
        if (!stats) return 'warn';
        const statuses = [
            statusForTotal(stats.total_manga),
            statusForScoreRate(stats.score_rate_pct),
            statusForUnscored(stats.unscored_manga),
            daysSinceUpdate === null ? 'warn' : statusForDays(daysSinceUpdate),
        ];
        if (statuses.includes('bad')) return 'bad';
        if (statuses.includes('warn')) return 'warn';
        return 'good';
    }, [stats, daysSinceUpdate]);

    if (loading && !stats && !sourceHealth && !scoreDist && !coverage && !topSearches && !mostViewed && !popularFilters && !watchlistData && !usersData) {
        return (
            <div className="admin-shell">
                <div className="admin-loading">BOOTING CONTROL ROOM...</div>
            </div>
        );
    }

    return (
        <div className="admin-shell">
            <header className={`admin-header admin-header-${headerStatus}`}>
                <div className="admin-header-brand">
                    <span>MANHWARANK</span>
                    <span className="admin-header-pill">ADMIN CONTROL ROOM</span>
                </div>
                <div className="admin-header-actions">
                    {lastFetch ? <span className="admin-muted">Fetched {lastFetch.toLocaleTimeString()}</span> : null}
                    <button className="admin-btn" onClick={() => loadAll({ silent: true })} disabled={refreshing}>
                        {refreshing ? 'Refreshing...' : 'Refresh'}
                    </button>
                    <a className="admin-link" href="/">Back to Site</a>
                    <button className="admin-btn admin-btn-ghost" onClick={onLogout}>Log Out</button>
                </div>
            </header>

            <main className="admin-main">
                {stats ? (
                    <motion.section
                        className="admin-kpi-grid"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <KPICard
                            label="Total Manga"
                            value={stats.total_manga.toLocaleString()}
                            status={statusForTotal(stats.total_manga)}
                            sublabel="manga_rankings"
                        />
                        <KPICard
                            label="Scored Manga"
                            value={stats.scored_manga.toLocaleString()}
                            status={statusForScoreRate(stats.score_rate_pct)}
                            sublabel={`${stats.score_rate_pct}% coverage`}
                        />
                        <KPICard
                            label="Unscored Manga"
                            value={stats.unscored_manga.toLocaleString()}
                            status={statusForUnscored(stats.unscored_manga)}
                            sublabel="missing source ratings"
                        />
                        <KPICard
                            label="Last Pipeline Run"
                            value={daysSinceUpdate === null ? 'Unknown' : daysSinceUpdate === 0 ? 'Today' : `${daysSinceUpdate}d ago`}
                            status={daysSinceUpdate === null ? 'warn' : statusForDays(daysSinceUpdate)}
                            sublabel={stats.last_updated ? new Date(stats.last_updated).toLocaleString() : 'no timestamp'}
                        />
                    </motion.section>
                ) : (
                    <PanelError message={errors.stats || 'Stats are unavailable.'} />
                )}

                <motion.section
                    className="admin-grid-2"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: 0.07 }}
                >
                    {sourceHealth ? <SourceHealthTable sources={sourceHealth} /> : <PanelError message={errors.source || 'Source health unavailable.'} />}
                    {scoreDist ? <ScoreDistributionChart data={scoreDist} /> : <PanelError message={errors.distribution || 'Distribution unavailable.'} />}
                </motion.section>

                <motion.section
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: 0.12 }}
                >
                    {coverage ? <SourceCoverageBar data={coverage} /> : <PanelError message={errors.coverage || 'Coverage unavailable.'} />}
                </motion.section>

                <motion.section
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2, delay: 0.18 }}
                >
                    <QuickActions />
                </motion.section>

                <motion.section
                    className="admin-panel"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: 0.24 }}
                >
                    <div className="admin-panel-title">Phase 2 Analytics</div>
                </motion.section>

                <motion.section
                    className="admin-grid-2"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: 0.28 }}
                >
                    {usersData ? <UserAnalyticsWidget data={usersData} /> : <PanelError message={errors.users || 'Active users unavailabe.'} />}
                    <UmamiWidget />
                </motion.section>

                <motion.section
                    className="admin-grid-2"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: 0.32 }}
                >
                    {topSearches ? <TopSearchesWidget data={topSearches} /> : <PanelError message={errors.top_searches || 'Top searches unavailable.'} />}
                    {mostViewed ? <MostViewedWidget data={mostViewed} /> : <PanelError message={errors.most_viewed || 'Most viewed manga unavailable.'} />}
                </motion.section>

                <motion.section
                    className="admin-grid-2"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: 0.36 }}
                >
                    {popularFilters ? <PopularFiltersWidget data={popularFilters} /> : <PanelError message={errors.popular_filters || 'Popular filters unavailable.'} />}
                    {watchlistData ? <WatchlistWidget data={watchlistData} /> : <PanelError message={errors.watchlist || 'Watchlist analytics unavailable.'} />}
                </motion.section>
            </main>
        </div>
    );
}
