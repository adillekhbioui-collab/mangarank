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
    const isInline = compactVariant === 'inline';
    const compactLabel = current ? STATUS_LABELS[current].toUpperCase() : '+ ADD';
    const compactGlyph = current ? '●' : '+';
    const overlayStyle = current
      ? { borderColor: STATUS_COLORS[current], color: STATUS_COLORS[current] }
      : {};

    return (
      <div
        className={
          isOverlay
            ? 'watchlist-compact inline-flex min-h-11 items-center gap-1 rounded border border-border/90 bg-background/92 px-2.5 font-mono text-[10px] tracking-[0.12em] text-text-primary shadow-[0_1px_3px_rgba(0,0,0,0.2)] backdrop-blur-sm'
            : isInline
              ? 'watchlist-compact inline-flex min-h-11 items-center rounded border border-border/90 bg-surface px-2.5 font-mono text-[10px] tracking-[0.12em] text-text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]'
              : 'watchlist-compact'
        }
        style={isOverlay || isInline ? overlayStyle : undefined}
        onClick={handleClick}
        title={current ? STATUS_LABELS[current] : 'Add to watchlist'}
        aria-label={current ? `${STATUS_LABELS[current]} in watchlist` : 'Add to watchlist'}
      >
        <span
          className={isOverlay ? 'text-[11px] leading-none' : ''}
          style={isOverlay || isInline ? undefined : { color: STATUS_COLORS[current] }}
        >
          {isOverlay ? compactGlyph : compactLabel}
        </span>
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
