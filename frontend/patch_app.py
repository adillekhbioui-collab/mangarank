import re

file_path = "src/App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()


# 1. Add viewMode state
state_block_old = r"""    // ── Local UI state ──
    const [results, setResults] = useState([])"""

state_block_new = """    // ── Local UI state ──
    const [viewMode, setViewMode] = useState('list')
    const [results, setResults] = useState([])"""

code = code.replace(state_block_old, state_block_new, 1)


# 2. Add Toggle Controls above results
render_old = r"""                <main className="content-area">
                    {loading && (
                        <div className="manga-list">
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
                            <div className="manga-list">"""

render_new = """                <main className="content-area">
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
                            <div className={viewMode === 'list' ? 'manga-list' : 'manga-grid'}>"""

code = code.replace(render_old, render_new, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("App.jsx updated.")
