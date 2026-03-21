import os

file_path = "src/SimilarManga.jsx"

new_content = """import { useState, useEffect, useCallback } from 'react'
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
                <div className="similar-list">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="similar-strip skeleton">
                            <div className="similar-strip-cover skeleton-box"></div>
                            <div className="similar-strip-info">
                                <div className="skeleton-line" style={{width: '60%'}}></div>
                                <div className="skeleton-line" style={{width: '40%'}}></div>
                            </div>
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
                <div className="similar-list">
                    {similar.map(m => (
                        <Link key={m.title} to={`/manga/${encodeURIComponent(m.title)}`} className="similar-strip">
                            <img
                                className="similar-strip-cover"
                                src={m.cover_image ? `${API_BASE}/proxy/image?url=${encodeURIComponent(m.cover_image)}` : 'https://placehold.co/100x150/141118/c1121f?text=NO+CVR'}
                                alt={m.title}
                                loading="lazy"
                                onError={(e) => {
                                    e.target.src = 'https://placehold.co/100x150/141118/c1121f?text=NO+CVR'
                                }}
                            />
                            <div className="similar-strip-info">
                                <h4 className="similar-strip-title">{m.title}</h4>
                                <div className="similar-strip-meta">
                                    <span>{m.aggregated_score || 'N/A'} SCORE</span>
                                    <span className="meta-pipe">|</span>
                                    <span>{m.chapter_count || 0} CH</span>
                                </div>
                                <div className="similar-strip-genres">
                                    {(m.genres || []).slice(0, 3).map(g => (
                                        <span key={g} className={`genre-tag ${targetGenreSet.has(g) ? 'genre-tag--shared' : ''}`}>
                                            {g.toUpperCase()}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </section>
    )
}
"""

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
