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

export function WatchlistButton({ manga, compact = false, compactVariant = 'default' }) {
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
    const isOverlay = compactVariant === 'overlay';
    const compactLabel = current ? STATUS_LABELS[current].toUpperCase() : '+ ADD';
    const overlayStyle = current
      ? { borderColor: STATUS_COLORS[current], color: STATUS_COLORS[current] }
      : {};

    return (
      <div
        className={isOverlay
          ? 'watchlist-compact inline-flex h-7 items-center rounded border border-border bg-background/85 px-2 font-mono text-[10px] tracking-[0.12em] text-text-primary backdrop-blur-sm'
          : 'watchlist-compact'}
        style={isOverlay ? overlayStyle : undefined}
        onClick={handleClick}
      >
        {current ? (
          <span style={isOverlay ? undefined : { color: STATUS_COLORS[current] }}>
            {compactLabel}
          </span>
        ) : (
          <span>{compactLabel}</span>
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
