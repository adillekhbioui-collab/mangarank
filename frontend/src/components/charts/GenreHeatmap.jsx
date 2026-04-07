import { Fragment, useMemo } from 'react'
import * as d3 from 'd3'

export default function GenreHeatmap({ data, onBrowseGenres, mobile = false }) {
    const topN = mobile ? 15 : 30
    const nodes = useMemo(() => [...(data.nodes || [])].sort((a, b) => b.manga_count - a.manga_count).slice(0, topN), [data.nodes, topN])
    const labels = nodes.map((n) => n.genre)
    const nodeCountMap = new Map(nodes.map((n) => [n.genre, n.manga_count]))
    const matrix = useMemo(() => {
        const m = new Map()
        data.edges.forEach((e) => {
            if (!nodeCountMap.has(e.genre_a) || !nodeCountMap.has(e.genre_b)) return
            m.set(`${e.genre_a}|${e.genre_b}`, e.co_occurrence)
            m.set(`${e.genre_b}|${e.genre_a}`, e.co_occurrence)
        })
        return m
    }, [data.edges, nodeCountMap])

    const maxEdge = Math.max(...data.edges.map((e) => e.co_occurrence), 1)
    const isLight = document.documentElement.getAttribute('data-theme') === 'light'
    const colorScale = d3.scaleLinear().domain([0, maxEdge]).range([isLight ? '#E4DED5' : '#1C1822', '#C1121F'])

    return (
        <div className="genre-heatmap-wrap">
            <div className="genre-heatmap-grid" style={{ gridTemplateColumns: `140px repeat(${labels.length}, minmax(24px, 1fr))` }}>
                <div />
                {labels.map((g) => <div key={`x-${g}`} className="heatmap-x-label">{g.toUpperCase()}</div>)}
                {labels.map((row) => (
                    <Fragment key={`row-${row}`}>
                        <div key={`y-${row}`} className="heatmap-y-label">{row.toUpperCase()}</div>
                        {labels.map((col, i) => {
                            const diagonal = row === col
                            const value = diagonal ? (nodeCountMap.get(row) || 0) : (matrix.get(`${row}|${col}`) || 0)
                            return (
                                <button
                                    key={`${row}-${col}-${i}`}
                                    className="heatmap-cell heatmap-row"
                                    style={{ '--heat': diagonal ? 'var(--accent-red)' : colorScale(value), animationDelay: `${i * 0.02}s` }}
                                    onClick={() => onBrowseGenres(diagonal ? [row] : [row, col])}
                                    title={`${row} + ${col}: ${value.toLocaleString()}`}
                                    aria-label={diagonal ? `Browse ${row}` : `Browse ${row} and ${col}`}
                                />
                            )
                        })}
                    </Fragment>
                ))}
            </div>
        </div>
    )
}
