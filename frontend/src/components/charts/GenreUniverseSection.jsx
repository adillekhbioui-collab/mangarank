import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import GenreNetwork from './GenreNetwork.jsx'
import GenreHeatmap from './GenreHeatmap.jsx'
import { fetchGenreRelationships } from '../../api.js'

export default function GenreUniverseSection({ onBrowseGenres }) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(false)
    const [view, setView] = useState('network')
    const [fullscreen, setFullscreen] = useState(false)
    const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 767px)').matches)

    useEffect(() => {
        const media = window.matchMedia('(max-width: 767px)')
        const onChange = (event) => setIsMobile(event.matches)
        media.addEventListener('change', onChange)
        return () => media.removeEventListener('change', onChange)
    }, [])

    useEffect(() => {
        let mounted = true
        fetchGenreRelationships()
            .then((res) => {
                if (!mounted) return
                setData(res)
                setError(false)
            })
            .catch(() => {
                if (!mounted) return
                setError(true)
            })
            .finally(() => {
                if (!mounted) return
                setLoading(false)
            })
        return () => { mounted = false }
    }, [])

    useEffect(() => {
        if (isMobile && view === 'network') setView('heatmap')
    }, [isMobile, view])

    const hasData = (data?.nodes?.length || 0) > 0 && (data?.edges?.length || 0) > 0

    if (loading) {
        return (
            <section className="genre-universe">
                <GenreUniverseHeader />
                <div className="network-skeleton">
                    {Array.from({ length: 20 }).map((_, i) => (
                        <div
                            key={i}
                            className="skeleton-bubble"
                            style={{
                                width: `${20 + Math.random() * 60}px`,
                                height: `${20 + Math.random() * 60}px`,
                                left: `${Math.random() * 80}%`,
                                top: `${Math.random() * 80}%`,
                                animationDelay: `${i * 0.1}s`,
                            }}
                        />
                    ))}
                    <p className="loading-text">Computing genre relationships...</p>
                </div>
            </section>
        )
    }

    if (error || !data) {
        return (
            <section className="genre-universe">
                <GenreUniverseHeader />
                <div className="genre-universe-error">
                    <span>Could not load genre relationships.</span>
                    <button onClick={() => window.location.reload()}>Retry</button>
                </div>
            </section>
        )
    }

    if (!hasData) {
        return (
            <section className="genre-universe">
                <GenreUniverseHeader totalGenres={data.meta?.total_genres} totalManga={data.meta?.total_manga} />
                <div className="genre-universe-error">
                    <span>No genre relationship data available yet.</span>
                    <button onClick={() => onBrowseGenres([])}>Back to Browse</button>
                </div>
            </section>
        )
    }

    return (
        <section className="genre-universe">
            <GenreUniverseHeader totalGenres={data.meta?.total_genres} totalManga={data.meta?.total_manga} />
            <div className="genre-universe-controls">
                {!isMobile && (
                    <div className="genre-view-toggle">
                        <button className={view === 'network' ? 'active' : ''} onClick={() => setView('network')}>○ Network</button>
                        <button className={view === 'heatmap' ? 'active' : ''} onClick={() => setView('heatmap')}>○ Heatmap</button>
                    </div>
                )}
                {!isMobile && <button className="fullscreen-toggle" onClick={() => setFullscreen(true)}>↗ Fullscreen</button>}
            </div>

            <AnimatePresence mode="wait" initial={false}>
                <motion.div
                    key={`${isMobile ? 'mobile' : 'desktop'}-${view}`}
                    className={`genre-view-shell ${view === 'network' ? 'view-enter' : 'view-enter'}`}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.18 }}
                >
                    {(!isMobile && view === 'network') ? (
                        <GenreNetwork data={data} onBrowseGenres={onBrowseGenres} />
                    ) : (
                        <GenreHeatmap data={data} onBrowseGenres={onBrowseGenres} mobile={isMobile} />
                    )}
                </motion.div>
            </AnimatePresence>

            <AnimatePresence>
                {fullscreen && (
                    <motion.div
                        className="fullscreen-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                    >
                        <button className="fullscreen-close" onClick={() => setFullscreen(false)}>✕ CLOSE</button>
                        <GenreNetwork data={data} onBrowseGenres={onBrowseGenres} fullscreen />
                    </motion.div>
                )}
            </AnimatePresence>
        </section>
    )
}

function GenreUniverseHeader({ totalGenres = 0, totalManga = 0 }) {
    return (
        <div className="genre-universe-header">
            <h2>GENRE UNIVERSE</h2>
            <div className="genre-universe-rule" />
            <p>How {totalGenres} genres relate across {Number(totalManga).toLocaleString()} manhwa & manhua.</p>
            <p>Aggregated from AniList · MAL · MangaDex · Kitsu</p>
        </div>
    )
}
