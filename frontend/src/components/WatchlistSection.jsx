import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useWatchlist } from '../hooks/useWatchlist';

export function WatchlistSection({ onBrowseWatchlist }) {
  const { grouped, totalCount } = useWatchlist();
  const [activeStatus, setActiveStatus] = useState('reading');
  const [showAll, setShowAll] = useState(false);

  const STATUS_META = {
    reading: { label: 'Currently reading', icon: '▶' },
    want_to_read: { label: 'Want to read', icon: '⊞' },
    completed: { label: 'Completed', icon: '✓' },
    dropped: { label: 'Dropped', icon: '×' },
  };

  const allEntries = useMemo(() => (
    Object.values(grouped)
      .flatMap((list) => list)
      .sort((a, b) => new Date(b[1].updated_at || b[1].added_at) - new Date(a[1].updated_at || a[1].added_at))
  ), [grouped]);

  const visibleEntries = showAll
    ? allEntries
    : (grouped[activeStatus] || []).slice(0, 6);

  function handleViewAllClick() {
    if (onBrowseWatchlist) {
      onBrowseWatchlist();
      return;
    }
    setShowAll((prev) => !prev);
  }

  if (totalCount === 0) {
    return (
      <section className="watchlist-section">
        <div className="watchlist-section-header">
          <h2>My Watchlist</h2>
          <div className="watchlist-section-rule" />
          <p>Save titles you want to read, are currently reading, or have completed.</p>
        </div>
        <div className="watchlist-section-empty">
          <p>Your watchlist is empty.</p>
          <p>Add titles using the <strong>+ Add to list</strong> button.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="watchlist-section">
      <WatchlistSectionHeader totalCount={totalCount} />

      <div className="watchlist-section-controls">
        <div className="watchlist-status-tabs">
          {Object.entries(STATUS_META).map(([key, meta]) => {
            const count = grouped[key]?.length || 0;
            return (
              <button
                key={key}
                type="button"
                className={`watchlist-status-tab ${activeStatus === key ? 'active' : ''}`}
                onClick={() => {
                  setActiveStatus(key);
                  setShowAll(false);
                }}
              >
                {meta.icon} {meta.label}
                <span className="watchlist-tab-count">{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="watchlist-section-preview">
        {visibleEntries.length === 0 ? (
          <p className="watchlist-preview-empty">
            {showAll ? 'Your watchlist is empty.' : 'Nothing in this category yet.'}
          </p>
        ) : (
          visibleEntries.map(([title, entry]) => (
            <Link
              key={title}
              to={`/manga/${encodeURIComponent(entry.title)}`}
              className="watchlist-preview-item"
            >
              <img
                src={entry.cover_url || 'https://placehold.co/220x300/1C1822/3D3545?text=No+Cover'}
                alt={entry.title}
                className="watchlist-preview-cover"
              />
              <div className="watchlist-preview-info">
                <span className="watchlist-preview-title">{entry.title}</span>
                <span className="watchlist-preview-date">
                  {new Date(entry.added_at || entry.updated_at).toLocaleDateString()}
                </span>
              </div>
            </Link>
          ))
        )}
      </div>

      <button type="button" className="watchlist-section-cta" onClick={handleViewAllClick}>
        {showAll ? 'Show less' : `View all ${totalCount} →`}
      </button>
    </section>
  );
}

function WatchlistSectionHeader({ totalCount }) {
  return (
    <div className="watchlist-section-header">
      <h2>My Watchlist</h2>
      <div className="watchlist-section-rule" />
      <p>{totalCount} titles saved across all categories.</p>
      <p>Synced to your browser · Export anytime</p>
    </div>
  );
}
