import { Link } from 'react-router-dom';
import { API_BASE } from '../api';
import { WatchlistButton } from './WatchlistButton.jsx';

function scoreTone(score) {
  if (score >= 90) return 'text-accent-gold';
  if (score >= 75) return 'text-text-primary';
  return 'text-text-secondary';
}

function statusTone(status) {
  if ((status || '').toLowerCase() === 'completed') {
    return 'text-accent-gold border-accent-gold/40';
  }
  return 'text-text-secondary border-border';
}

export function MangaCard({ manga, rank, viewMode, onTrackClick }) {
  const badgeLabel = manga.status ? manga.status : 'ONGOING';
  const cardScoreTone = scoreTone(manga.aggregated_score ?? -1);
  const cardStatusTone = statusTone(badgeLabel);
  const coverSrc = manga.cover_image
    ? `${API_BASE}/proxy/image?url=${encodeURIComponent(manga.cover_image)}`
    : 'https://placehold.co/220x330/1C1822/3D3545?text=No+Cover';
  const fallbackCover = 'https://placehold.co/220x330/1C1822/3D3545?text=No+Cover';

  if (viewMode === 'grid') {
    return (
      <Link
        to={`/manga/${encodeURIComponent(manga.title)}`}
        className="group relative overflow-hidden border border-border bg-elevated transition-colors hover:bg-surface"
        onClick={onTrackClick}
      >
        <div className="absolute left-1.5 top-1.5 z-10 rounded bg-background/75 px-1.5 py-0.5 font-mono text-[10px] text-text-secondary backdrop-blur-sm">{rank}</div>
        <div className="absolute right-1.5 top-1.5 z-10">
          <WatchlistButton manga={manga} compact compactVariant="overlay" />
        </div>

        <div className="aspect-[3/4] overflow-hidden border-b border-border bg-background">
          <img
            className="h-full w-full object-cover"
            src={coverSrc}
            alt={manga.title}
            loading="lazy"
            onError={(event) => {
              event.currentTarget.onerror = null;
              event.currentTarget.src = fallbackCover;
            }}
          />
        </div>

        <div className="space-y-1.5 p-2">
          <h3 className="line-clamp-2 font-serif text-[13px] leading-tight text-text-primary">{manga.title}</h3>
          <div className="truncate text-[10px] text-text-secondary">{manga.author || 'Unknown Author'}</div>

          <div className="flex items-center justify-between">
            <div className="flex items-end gap-1">
              <span className={`font-mono text-lg leading-none ${cardScoreTone}`}>
                {manga.aggregated_score != null ? Math.round(manga.aggregated_score) : '?'}
              </span>
              <span className="mb-0.5 font-mono text-[9px] tracking-[0.1em] text-text-ghost">SCORE</span>
            </div>
            <span className={`rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.08em] ${cardStatusTone}`}>
              {badgeLabel}
            </span>
          </div>

          <div className="text-[9px] text-text-ghost">
            {manga.chapter_count || 0} ch.
            <span className="mx-1">·</span>
            {manga.total_views ? manga.total_views.toLocaleString() : '0'} views
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link
      to={`/manga/${encodeURIComponent(manga.title)}`}
      className="group grid min-h-[156px] grid-cols-[2.25rem_6rem_minmax(0,1fr)] border border-border bg-elevated transition-colors hover:bg-surface sm:min-h-[164px] sm:grid-cols-[2.5rem_6.875rem_minmax(0,1fr)]"
      onClick={onTrackClick}
    >
      <div className="flex items-center justify-center border-r border-border/60 bg-background/35 font-mono text-sm text-text-secondary">
        {rank}
      </div>

      <div className="relative isolate self-stretch overflow-hidden bg-background">
        <img
          className="h-full w-full object-cover transition-transform duration-300 ease-out group-hover:scale-105"
          src={coverSrc}
          alt={manga.title}
          loading="lazy"
          onError={(event) => {
            event.currentTarget.onerror = null;
            event.currentTarget.src = fallbackCover;
          }}
        />
        <div className="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-r from-transparent via-background/20 to-elevated/95 transition-colors group-hover:to-surface/95" />
      </div>

      <div className="min-w-0 px-3 py-3 sm:px-4 sm:py-3.5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <h3 className="line-clamp-2 font-serif text-[16px] leading-tight text-text-primary">{manga.title}</h3>
          <div className="self-start">
            <WatchlistButton manga={manga} compact compactVariant="inline" />
          </div>
        </div>

        <div className="mt-1 truncate text-xs text-text-secondary">{manga.author || 'Unknown Author'}</div>
        <div className="mt-1 line-clamp-1 text-xs text-text-ghost">{(manga.genres || []).slice(0, 4).join(' · ')}</div>

        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-text-secondary">
          <span>{manga.chapter_count || 0} ch.</span>
          <span>|</span>
          <span>{manga.total_views ? manga.total_views.toLocaleString() : '0'} views</span>
          <span className={`rounded border px-1.5 py-0.5 uppercase tracking-[0.08em] ${cardStatusTone}`}>{badgeLabel}</span>
        </div>

        <div className="mt-2 flex items-end gap-1">
          <span className={`font-mono text-2xl leading-none ${cardScoreTone}`}>
            {manga.aggregated_score != null ? Math.round(manga.aggregated_score) : '?'}
          </span>
          <span className="mb-0.5 font-mono text-[10px] tracking-[0.12em] text-text-ghost">SCORE</span>
        </div>
      </div>
    </Link>
  );
}

export function MangaCardSkeleton({ viewMode }) {
  if (viewMode === 'grid') {
    return (
      <div className="overflow-hidden border border-border bg-surface">
        <div className="aspect-[3/4] animate-pulse bg-background" />
        <div className="space-y-2 p-2">
          <div className="h-3 w-4/5 animate-pulse bg-background" />
          <div className="h-2.5 w-2/3 animate-pulse bg-background" />
          <div className="h-2.5 w-1/2 animate-pulse bg-background" />
        </div>
      </div>
    );
  }

  return <div className="h-[164px] animate-pulse border border-border bg-surface" />;
}
