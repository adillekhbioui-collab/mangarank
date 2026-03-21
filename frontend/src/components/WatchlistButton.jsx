import { useEffect, useRef, useState } from 'react';
import { useWatchlist } from '../hooks/useWatchlist';

const STATUS_LABELS = {
  want_to_read: 'Want to read',
  reading: 'Reading',
  completed: 'Completed',
  dropped: 'Dropped',
};

const STATUS_COLORS = {
  want_to_read: 'var(--watchlist-want)',
  reading: 'var(--watchlist-reading)',
  completed: 'var(--watchlist-done)',
  dropped: 'var(--watchlist-drop)',
};

export function WatchlistButton({ manga, compact = false }) {
  const { getStatus, addOrUpdate, remove, STATUSES } = useWatchlist();
  const current = getStatus(manga.title);
  const [menuOpen, setMenuOpen] = useState(false);
  const groupRef = useRef(null);

  useEffect(() => {
    function handleDocumentClick(event) {
      if (!groupRef.current) return;
      if (!groupRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener('mousedown', handleDocumentClick);
    return () => document.removeEventListener('mousedown', handleDocumentClick);
  }, []);

  useEffect(() => {
    if (!current) {
      setMenuOpen(false);
    }
  }, [current]);

  function handleClick(e) {
    e.preventDefault();
    e.stopPropagation();
    if (!current) {
      addOrUpdate(manga.title, manga, 'want_to_read');
      setMenuOpen(false);
      return;
    }

    setMenuOpen((prev) => !prev);
  }

  function handleStatusSelect(e, status) {
    e.preventDefault();
    e.stopPropagation();
    if (current === status) {
      remove(manga.title);
    } else {
      addOrUpdate(manga.title, manga, status);
    }
    setMenuOpen(false);
  }

  if (compact) {
    return (
      <div className="watchlist-compact" onClick={handleClick}>
        {current ? (
          <span style={{ color: STATUS_COLORS[current] }}>
            {STATUS_LABELS[current]}
          </span>
        ) : (
          <span>+ Add</span>
        )}
      </div>
    );
  }

  return (
    <div className="watchlist-btn-group" ref={groupRef}>
      <button
        type="button"
        className={`watchlist-btn ${current ? 'active' : ''}`}
        style={current ? { borderColor: STATUS_COLORS[current], color: STATUS_COLORS[current] } : {}}
        onClick={handleClick}
      >
        {current ? STATUS_LABELS[current] : '+ Add to list'}
      </button>

      {current && menuOpen && (
        <div className="watchlist-dropdown">
          {STATUSES.map((s) => (
            <button
              type="button"
              key={s}
              className={`watchlist-dropdown-item ${s === current ? 'selected' : ''}`}
              onClick={(e) => handleStatusSelect(e, s)}
            >
              {STATUS_LABELS[s]}
              {s === current && <span className="remove-hint">(tap to remove)</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
