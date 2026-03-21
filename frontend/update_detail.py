import re

with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/MangaDetailPage.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

new_content = """import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchMangaByTitle, API_BASE } from './api'
import SimilarManga from './SimilarManga.jsx'

export default function MangaDetailPage() {
    const { title } = useParams()
    const [manga, setManga] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [synopsisExpanded, setSynopsisExpanded] = useState(false)

    useEffect(() => {
        setLoading(true)
        setError(null)
        setManga(null)
        setSynopsisExpanded(false)
        fetchMangaByTitle(decodeURIComponent(title))
            .then(data => setManga(data))
            .catch(err => setError(err.message))
            .finally(() => setLoading(false))
    }, [title])

    if (loading) return <DetailSkeleton />
    if (error) return <ErrorView message={error} />

    const badgeLabel = manga.status ? manga.status : 'ONGOING';

    return (
        <>
            <header className="site-header">
                <div className="header-left">
                    <Link to="/" className="logo">
                        <span className="logo-manhwa">MANHWA</span>
                        <span className="logo-rank">RANK</span>
                    </Link>
                </div>
            </header>

            <div className="detail-page">
                <div className="detail-top">
                    <div className="detail-cover-col">
                        <img
                            className="detail-cover"
                            src={manga.cover_image
                                ? `${API_BASE}/proxy/image?url=${encodeURIComponent(manga.cover_image)}`
                                : 'https://placehold.co/240x340/1C1822/3D3545?text=No+Cover'
                            }
                            alt={manga.title}
                        />
                        <div className="detail-attribution">
                            DATA AGGREGATED FROM MANGADEX, ANILIST & KITSU
                        </div>
                    </div>

                    <div className="detail-info-col">
                        <h1 className="detail-title">{manga.title}</h1>
                        <p className="detail-author">by {manga.author || 'Unknown Author'}</p>

                        <div className="detail-stats-row">
                            <div className="detail-stat">
                                <span className="stat-label">SCORE</span>
                                <span className="stat-value accent">{manga.aggregated_score ?? '—'}</span>
                            </div>
                            <div className="detail-stat">
                                <span className="stat-label">CHAPTERS</span>
                                <span className="stat-value">{manga.chapter_count || 0}</span>
                            </div>
                            <div className="detail-stat">
                                <span className="stat-label">VIEWS</span>
                                <span className="stat-value">{manga.total_views ? manga.total_views.toLocaleString() : '—'}</span>
                            </div>
                            <div className="detail-stat">
                                <span className="stat-label">STATUS</span>
                                <span className="stat-value text-ghost">{badgeLabel.toUpperCase()}</span>
                            </div>
                        </div>

                        {manga.completion_rate !== null && manga.total_readers >= 100 && (
                            <div className="detail-completion-wrap">
                                <div className="completion-bar-bg">
                                    <div 
                                        className="completion-bar-fill" 
                                        style={{ 
                                            width: `${manga.completion_rate}%`,
                                            backgroundColor: manga.completion_rate >= 70 ? 'var(--accent-gold)' : (manga.completion_rate < 40 ? 'var(--text-ghost)' : 'var(--accent-red)') 
                                        }}
                                    ></div>
                                </div>
                                <div className="completion-texts">
                                    <span className="completion-pct">{manga.completion_rate}%</span>
                                    <span className="completion-label">
                                        {manga.completion_rate >= 70 ? 'High completion rate (Masterpiece tier)' 
                                            : manga.completion_rate >= 40 ? 'Average completion rate' 
                                            : 'Many readers drop this title'}    
                                    </span>
                                </div>
                            </div>
                        )}

                        <div className="detail-genres">
                            {(manga.genres || []).map(g => (
                                <span key={g} className="detail-genre-tag">{g}</span>
                            ))}
                        </div>

                        {manga.summary && (
                            <>
                                <div className={`detail-synopsis ${!synopsisExpanded ? 'collapsed' : ''}`}>
                                    {manga.summary}
                                </div>
                                <button className="synopsis-toggle" onClick={() => setSynopsisExpanded(!synopsisExpanded)}>
                                    {synopsisExpanded ? 'READ LESS' : 'READ MORE'}
                                </button>
                            </>
                        )}
                    </div>
                </div>

                <SimilarManga
                    title={manga.title}
                    genres={manga.genres || []}
                />
            </div>
        </>
    )
}

function DetailSkeleton() {
    return (
        <>
            <header className="site-header">
                <div className="header-left">
                    <Link to="/" className="logo">
                        <span className="logo-manhwa">MANHWA</span>
                        <span className="logo-rank">RANK</span>
                    </Link>
                </div>
            </header>
            <div className="detail-page">
                <div className="detail-top">
                    <div className="detail-cover-col">
                        <div className="skeleton-strip" style={{ width: '100%', height: '340px' }} />
                    </div>
                    <div className="detail-info-col">
                        <div className="skeleton-strip" style={{ height: '36px', width: '70%', marginBottom: '12px' }} />
                        <div className="skeleton-strip" style={{ height: '18px', width: '40%', marginBottom: '32px' }} />
                        <div className="skeleton-strip" style={{ height: '64px', width: '100%', marginBottom: '32px' }} />
                        <div className="skeleton-strip" style={{ height: '14px', width: '100%', marginBottom: '8px' }} />
                        <div className="skeleton-strip" style={{ height: '14px', width: '100%', marginBottom: '8px' }} />
                    </div>
                </div>
            </div>
        </>
    )
}

function ErrorView({ message }) {
    return (
        <>
            <header className="site-header">
                <div className="header-left">
                    <Link to="/" className="logo">
                        <span className="logo-manhwa">MANHWA</span>
                        <span className="logo-rank">RANK</span>
                    </Link>
                </div>
            </header>
            <div className="detail-page" style={{ textAlign: 'center', marginTop: '48px', fontFamily: 'var(--font-data)' }}>
                <div className="text-secondary" style={{ fontSize: '48px', marginBottom: '16px' }}>404</div>
                <div className="text-primary">{message || 'MANGA NOT FOUND'}</div>
                <Link to="/" className="text-accent-red" style={{ display: 'inline-block', marginTop: '24px', letterSpacing: '0.1em' }}>
                    ← BACK TO BROWSE
                </Link>
            </div>
        </>
    )
}
"""

with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/MangaDetailPage.jsx', 'w', encoding='utf-8') as f:
    f.write(new_content)
