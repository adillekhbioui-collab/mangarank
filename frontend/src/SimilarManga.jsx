import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { fetchSimilarManga, API_BASE } from './api'

export default function SimilarManga({ title, genres }) {
    const [similar, setSimilar] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(false)

    const targetGenreSet = new Set(genres || [])

    const load = useCallback(async (bypass = false) => {
        setLoading(true)
        setError(false)
        try {
            const results = await fetchSimilarManga(title, { bypassCache: bypass })
            setSimilar(results)
        } catch {
            setError(true)
            setSimilar([])
        }
        setLoading(false)
    }, [title])

    useEffect(() => { load() }, [load])

    const handleRefresh = () => load(true)

    return (
        <section className="similar-section">
            <div className="similar-header">
                <span className="section-label">SIMILAR MANGA</span>
                <div className="section-line"></div>
                <button className="refresh-btn" onClick={handleRefresh} disabled={loading}>
                    REFRESH
                </button>
            </div>

            {loading && (
                <div className="manga-list">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="manga-strip skeleton-strip" style={{height: '110px'}}>
                        </div>
                    ))}
                </div>
            )}

            {!loading && error && (
                <div className="similar-error">Could not load recommendations.</div>
            )}

            {!loading && !error && similar.length === 0 && (
                <div className="similar-empty">No similar manga found.</div>
            )}

            {!loading && !error && similar.length > 0 && (
                <div className="manga-list">
                    {similar.map(m => {
                        let scoreColorClass = 'low';
                        if (m.aggregated_score >= 90) scoreColorClass = 'gold';
                        else if (m.aggregated_score >= 75) scoreColorClass = 'normal';

                        return (
                            <Link key={m.title} to={`/manga/${encodeURIComponent(m.title)}`} className="manga-strip">
                                <div className="strip-cover-col">
                                    <img
                                        className="strip-cover"
                                        src={m.cover_image ? `${API_BASE}/proxy/image?url=${encodeURIComponent(m.cover_image)}` : 'https://placehold.co/110x160/141118/c1121f?text=NO+CVR'}
                                        alt={m.title}
                                        loading="lazy"
                                        onError={(e) => {
                                            e.target.src = 'https://placehold.co/110x160/141118/c1121f?text=NO+CVR'
                                        }}
                                    />
                                </div>
                                <div className="strip-meta-col">
                                    <h3 className="strip-title">{m.title}</h3>
                                    <div className="strip-genres" style={{ flexWrap: 'wrap', overflow: 'hidden', maxHeight: '28px' }}>
                                        {(m.genres || []).slice(0, 5).map(g => (
                                            <span key={g} className={`genre-tag ${targetGenreSet.has(g) ? 'genre-tag--shared' : ''}`}>
                                                {g.toUpperCase()}
                                            </span>
                                        ))}
                                    </div>
                                    <div className="strip-stats">
                                        <span className="stat-value">{m.chapter_count || 0}</span> <span className="stat-label">CH</span>
                                    </div>
                                </div>
                                <div className="strip-score-col">
                                    <span className={`strip-score ${scoreColorClass}`}>{m.aggregated_score || 'N/A'}</span>
                                    <span className="score-label">SCORE</span>
                                </div>
                            </Link>
                        )
                    })}
                </div>
            )}
        </section>
    )
}
