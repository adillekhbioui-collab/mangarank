const fs = require('fs');
const p = 'C:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/App.jsx';
let code = fs.readFileSync(p, 'utf8');
const search = `            {topTab === 'charts' && (
                <div className="main-layout">
                    <main className="content-area">
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
            )}`;

const insert = `            {topTab === 'watchlist' && (
                <div className="main-layout">
                    <main className="content-area">
                        <WatchlistSection onBrowseWatchlist={() => setTopTab('browse')} />
                    </main>
                </div>
            )}`;

code = code.replace(search, search + '\n' + insert);
fs.writeFileSync(p, code);
