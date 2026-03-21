import { useEffect, useMemo, useRef, useState } from 'react'
import * as d3 from 'd3'
import { AnimatePresence, motion } from 'motion/react'
import { fetchManga } from '../../api.js'

let hasRenderedNetworkBefore = false

export default function GenreNetwork({ data, onBrowseGenres, fullscreen = false }) {
    const containerRef = useRef(null)
    const svgRef = useRef(null)
    const simRef = useRef(null)

    const [dimensions, setDimensions] = useState({ width: 0, height: fullscreen ? 640 : 600 })
    const [selected, setSelected] = useState(null)
    const [edgeTooltip, setEdgeTooltip] = useState(null)
    const [topManga, setTopManga] = useState([])
    const [loadingTopManga, setLoadingTopManga] = useState(false)

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const nodeByGenre = useMemo(
        () => new Map((data?.nodes || []).map((n) => [n.genre, n])),
        [data?.nodes],
    )

    const relatedGenres = useMemo(() => {
        if (!selected?.genre) return []
        return (data?.edges || [])
            .filter((e) => e.genre_a === selected.genre || e.genre_b === selected.genre)
            .map((e) => ({
                genre: e.genre_a === selected.genre ? e.genre_b : e.genre_a,
                count: e.co_occurrence,
            }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 5)
    }, [data?.edges, selected?.genre])

    useEffect(() => {
        const container = containerRef.current
        if (!container) return undefined

        const observer = new ResizeObserver((entries) => {
            entries.forEach((entry) => {
                const { width, height } = entry.contentRect
                const safeHeight = fullscreen ? Math.max(Math.floor(height), 640) : Math.max(Math.floor(height), 600)
                if (width > 0 && safeHeight > 0) {
                    setDimensions({ width: Math.floor(width), height: safeHeight })
                }
            })
        })

        observer.observe(container)
        return () => observer.disconnect()
    }, [fullscreen])

    useEffect(() => {
        if (!selected?.genre) {
            setTopManga([])
            return
        }

        let mounted = true
        setLoadingTopManga(true)
        fetchManga({ genre_include: [selected.genre], sort_by: 'score', limit: 3, page: 1 })
            .then((res) => {
                if (!mounted) return
                setTopManga(res?.results || [])
            })
            .catch(() => {
                if (!mounted) return
                setTopManga([])
            })
            .finally(() => {
                if (!mounted) return
                setLoadingTopManga(false)
            })

        return () => { mounted = false }
    }, [selected?.genre])

    useEffect(() => {
        if (!data?.nodes?.length || dimensions.width === 0 || dimensions.height === 0 || !svgRef.current) return undefined

        const width = dimensions.width
        const height = dimensions.height
        const svg = d3.select(svgRef.current)

        svg.attr('width', width).attr('height', height)
        svg.selectAll('*').remove()

        const maxCount = Math.max(...data.nodes.map((n) => n.manga_count || 0), 1)
        const nodes = data.nodes.map((n) => ({
            ...n,
            id: n.genre,
            radius: 8 + ((n.manga_count || 0) / maxCount) * 32,
        }))
        const filteredEdges = (data.edges || [])
            .sort((a, b) => (b.co_occurrence || 0) - (a.co_occurrence || 0))

        const edges = filteredEdges.map((e) => ({
            ...e,
            source: e.genre_a,
            target: e.genre_b,
        }))

        const zoomLayer = svg.append('g').attr('class', 'zoom-layer')

        const edgeSelection = zoomLayer.append('g')
            .attr('class', 'edges')
            .selectAll('line')
            .data(edges)
            .join('line')
            .attr('class', 'genre-link')
            .attr('stroke', 'var(--border)')
            .attr('stroke-width', (d) => 0.65 + (d.strength || 0) * 2.15)
            .attr('stroke-linecap', 'round')
            .attr('vector-effect', 'non-scaling-stroke')
            .attr('shape-rendering', 'geometricPrecision')
            .style('cursor', 'pointer')
            .on('click', (event, d) => {
                event.stopPropagation()
                const rect = containerRef.current?.getBoundingClientRect()
                if (!rect) return
                const rawX = event.clientX - rect.left + 10
                const rawY = event.clientY - rect.top + 10
                const x = Math.min(Math.max(8, rawX), Math.max(8, width - 270))
                const y = Math.min(Math.max(8, rawY), Math.max(8, height - 110))
                setEdgeTooltip({
                    x,
                    y,
                    edge: d,
                })
            })

        // Initial opacities/displays
        const isStrongEdge = (d) => (d.strength || 0) >= 0.06 || (d.co_occurrence || 0) >= 120
        edgeSelection
            .attr('stroke-opacity', (d) => isStrongEdge(d) ? 0.22 : 0)
            .style('display', (d) => isStrongEdge(d) ? 'inline' : 'none')

        const zoomBehavior = d3.zoom().scaleExtent([0.5, 3]).on('zoom', (event) => {
            zoomLayer.attr('transform', event.transform)
            
            // Dynamic edge opacity
            edgeSelection
                .attr('stroke-opacity', (d) => {
                    if (isStrongEdge(d)) return 0.22
                    const t = Math.max(0, Math.min(1, (event.transform.k - 1) / 1.5))
                    return t * 0.22
                })
                .style('display', (d) => {
                    if (isStrongEdge(d)) return 'inline'
                    return event.transform.k > 1.05 ? 'inline' : 'none'
                })
        })
        svg.call(zoomBehavior)
        svgRef.current.__zoomBehavior = zoomBehavior

        const nodeGroup = zoomLayer.append('g')
            .attr('class', 'nodes')
            .selectAll('g')
            .data(nodes)
            .join('g')
            .attr('class', 'node-group')
            .style('cursor', 'pointer')

        nodeGroup.append('circle')
            .attr('class', 'genre-node')
            .attr('data-genre', (d) => d.genre)
            .attr('fill', 'var(--bg-elevated)')
            .attr('stroke', 'var(--border)')
            .attr('stroke-width', 1)
            .attr('r', reducedMotion || hasRenderedNetworkBefore ? (d) => d.radius : 0)

        nodeGroup.append('text')
            .attr('class', 'genre-label')
            .text((d) => d.genre.toUpperCase())
            .attr('text-anchor', 'middle')
            .attr('dy', (d) => d.radius + 13)
            .attr('fill', 'var(--text-secondary)')
            .attr('font-family', 'var(--font-data)')
            .attr('font-size', '9px')
            .attr('letter-spacing', '0.1em')
            .style('pointer-events', 'none')

        nodeGroup.on('click', (event, d) => {
            event.stopPropagation()
            setSelected({
                genre: d.genre,
                manga_count: d.manga_count,
                avg_score: d.avg_score,
            })
        })

        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(edges)
                .id((d) => d.id)
                .strength((d) => (d.strength || 0) * 0.25)
                .distance((d) => 100 - (d.strength || 0) * 50))
            .force('charge', d3.forceManyBody().strength(-250))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius((d) => d.radius + 12))
            .force('x', d3.forceX(width / 2).strength(0.05))
            .force('y', d3.forceY(height / 2).strength(0.05))

        const applyPositions = () => {
            nodes.forEach((n) => {
                n.x = Math.max(n.radius + 10, Math.min(width - n.radius - 10, n.x))
                n.y = Math.max(n.radius + 10, Math.min(height - n.radius - 10, n.y))
            })

            edgeSelection
                .attr('x1', (d) => d.source.x)
                .attr('y1', (d) => d.source.y)
                .attr('x2', (d) => d.target.x)
                .attr('y2', (d) => d.target.y)

            nodeGroup.attr('transform', (d) => `translate(${d.x}, ${d.y})`)
        }

        simulation.on('tick', applyPositions)

        simRef.current = simulation

        if (reducedMotion || hasRenderedNetworkBefore) {
            simulation.stop()
            for (let i = 0; i < 300; i += 1) simulation.tick()
            applyPositions()
        } else {
            nodeGroup.select('circle')
                .transition()
                .duration(400)
                .delay((_, i) => i * 8)
                .attr('r', (d) => d.radius)

            edgeSelection
                .attr('stroke-dasharray', function getLen() { return this.getTotalLength() })
                .attr('stroke-dashoffset', function getLen() { return this.getTotalLength() })
                .transition()
                .duration(600)
                .delay(400)
                .attr('stroke-dashoffset', 0)

            hasRenderedNetworkBefore = true
        }

        svg.on('click', () => {
            setSelected(null)
            setEdgeTooltip(null)
        })

        return () => {
            if (simRef.current) simRef.current.stop()
        }
    }, [data, dimensions, reducedMotion])

    useEffect(() => {
        const svg = d3.select(svgRef.current)
        const circles = svg.selectAll('.genre-node')
        const links = svg.selectAll('.genre-link')
        const labels = svg.selectAll('.genre-label')

        if (!selected?.genre) {
            circles.transition().duration(250)
                .attr('opacity', 1)
                .attr('stroke-width', 1)
                .attr('stroke', 'var(--border)')
                .attr('fill', 'var(--bg-elevated)')
            labels.transition().duration(250)
                .attr('opacity', 1)
                .attr('fill', 'var(--text-secondary)')
            links.transition().duration(250)
                .attr('stroke-opacity', 0.4)
                .attr('stroke', 'var(--border)')
            return
        }

        const connected = new Set([selected.genre])
        ;(data?.edges || []).forEach((e) => {
            if (e.genre_a === selected.genre || e.genre_b === selected.genre) {
                connected.add(e.genre_a)
                connected.add(e.genre_b)
            }
        })

        circles.transition().duration(250)
            .attr('opacity', (d) => (connected.has(d.genre) ? 1 : 0.15))
            .attr('stroke-width', (d) => (d.genre === selected.genre ? 2 : 1))
            .attr('stroke', (d) => (d.genre === selected.genre ? 'var(--accent-red)' : 'var(--border)'))
            .attr('fill', (d) => (d.genre === selected.genre ? 'rgba(193, 18, 31, 0.30)' : 'var(--bg-elevated)'))

        labels.transition().duration(250)
            .attr('opacity', (d) => (connected.has(d.genre) ? 1 : 0.2))
            .attr('fill', (d) => (d.genre === selected.genre ? 'var(--accent-red)' : 'var(--text-secondary)'))

        links.transition().duration(250)
            .attr('stroke-opacity', (d) => (d.genre_a === selected.genre || d.genre_b === selected.genre ? 0.55 : 0.02))
            .attr('stroke', (d) => (d.genre_a === selected.genre || d.genre_b === selected.genre ? 'var(--accent-red)' : 'var(--border)'))
    }, [selected, data?.edges])

    const zoomBy = (factor) => {
        const svg = d3.select(svgRef.current)
        const zoom = svgRef.current?.__zoomBehavior
        if (!zoom || !svgRef.current) return
        svg.transition().duration(220).call(zoom.scaleBy, factor)
    }

    const resetView = () => {
        const svg = d3.select(svgRef.current)
        const zoom = svgRef.current?.__zoomBehavior
        if (!zoom || !svgRef.current) return
        svg.transition().duration(260).call(zoom.transform, d3.zoomIdentity)
    }

    if (!data?.nodes?.length) {
        return (
            <div
                className="genre-network-container"
                style={{
                    position: 'relative',
                    width: '100%',
                    height: fullscreen ? 'calc(100vh - 120px)' : '600px',
                }}
            >
                <LoadingState />
            </div>
        )
    }

    const safeHeight = fullscreen ? 'calc(100vh - 120px)' : '600px'

    return (
        <div
            ref={containerRef}
            className="genre-network-container"
            style={{
                position: 'relative',
                width: '100%',
                height: safeHeight,
                background: 'var(--bg-primary)',
            }}
        >
            <div className="network-tools">
                <button className="network-tool-btn" onClick={() => zoomBy(1.2)}>+</button>
                <button className="network-tool-btn" onClick={() => zoomBy(0.8)}>−</button>
                <button className="network-reset" onClick={resetView}>Reset view</button>
            </div>

            <svg
                ref={svgRef}
                className="genre-network-svg"
                width={dimensions.width}
                height={dimensions.height}
                style={{ display: 'block', overflow: 'visible' }}
            />

            {edgeTooltip && (
                <EdgeTooltip
                    tooltip={edgeTooltip}
                    onBrowseBoth={() => onBrowseGenres([edgeTooltip.edge.genre_a, edgeTooltip.edge.genre_b])}
                />
            )}

            <AnimatePresence>
                {selected && (
                    <DetailPanel
                        genre={selected}
                        relatedGenres={relatedGenres}
                        topManga={topManga}
                        loadingTopManga={loadingTopManga}
                        onClose={() => setSelected(null)}
                        onBrowseGenres={onBrowseGenres}
                    />
                )}
            </AnimatePresence>
        </div>
    )
}

function DetailPanel({ genre, relatedGenres, topManga, loadingTopManga, onClose, onBrowseGenres }) {
    return (
        <motion.aside
            className="genre-detail-panel"
            initial={{ x: 300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 300, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
            <button className="genre-detail-close" onClick={onClose}>✕</button>
            <motion.h3 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
                {genre.genre}
            </motion.h3>

            <motion.div className="genre-detail-stats" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                <div>
                    <span>MANGA COUNT</span>
                    <strong>{Number(genre.manga_count || 0).toLocaleString()}</strong>
                </div>
                <div>
                    <span>AVERAGE SCORE</span>
                    <strong>{genre.avg_score ?? '—'} / 100</strong>
                </div>
            </motion.div>

            <motion.div className="genre-detail-related" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
                <div className="genre-detail-label">TOP RELATED GENRES</div>
                {relatedGenres.map((rel) => (
                    <button key={rel.genre} className="genre-related-row" onClick={() => onBrowseGenres([genre.genre, rel.genre])}>
                        <span>{rel.genre}</span>
                        <span>{Number(rel.count || 0).toLocaleString()} shared</span>
                    </button>
                ))}
            </motion.div>

            <motion.div className="genre-detail-related" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                <div className="genre-detail-label">TOP 3 MANGA IN THIS GENRE</div>
                {loadingTopManga && <div className="text-ghost" style={{ fontFamily: 'var(--font-data)', fontSize: '10px' }}>Loading...</div>}
                {!loadingTopManga && topManga.length === 0 && (
                    <div className="text-ghost" style={{ fontFamily: 'var(--font-data)', fontSize: '10px' }}>No results</div>
                )}
                {!loadingTopManga && topManga.map((m) => (
                    <div key={m.title} className="genre-related-row" style={{ cursor: 'default' }}>
                        <span style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.title}</span>
                        <span>{m.aggregated_score ?? '—'}</span>
                    </div>
                ))}
            </motion.div>

            <motion.button
                className="genre-browse-link"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
                onClick={() => onBrowseGenres([genre.genre])}
            >
                Browse all {genre.genre} manga →
            </motion.button>
        </motion.aside>
    )
}

function EdgeTooltip({ tooltip, onBrowseBoth }) {
    return (
        <div className="network-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
            <div>{tooltip.edge.genre_a.toUpperCase()} + {tooltip.edge.genre_b.toUpperCase()}</div>
            <div>{Number(tooltip.edge.co_occurrence || 0).toLocaleString()} manga share both genres</div>
            <button className="network-tooltip-link" onClick={onBrowseBoth}>Browse both →</button>
        </div>
    )
}

function LoadingState() {
    return (
        <div
            style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '14px',
            }}
        >
            <div style={{ position: 'relative', width: '58px', height: '58px' }}>
                {[0, 1, 2].map((i) => (
                    <div
                        key={i}
                        style={{
                            position: 'absolute',
                            inset: 0,
                            borderRadius: '50%',
                            border: '1px solid var(--border)',
                            animation: `genreNetworkPing 1.5s ease-out ${i * 0.35}s infinite`,
                        }}
                    />
                ))}
            </div>
            <p
                style={{
                    fontFamily: 'var(--font-data)',
                    fontSize: '11px',
                    color: 'var(--text-ghost)',
                    letterSpacing: '0.15em',
                    textTransform: 'uppercase',
                }}
            >
                Computing genre relationships...
            </p>
            <style>{`@keyframes genreNetworkPing { 0% { transform: scale(0.5); opacity: 0.8; } 100% { transform: scale(2.5); opacity: 0; } }`}</style>
        </div>
    )
}
