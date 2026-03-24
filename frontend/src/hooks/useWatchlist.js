import { useState, useEffect } from 'react';
import { API_BASE } from '../api';
import { trackAnalytics } from './useAnalytics.js';

const STORAGE_KEY = 'manga_watchlist';

function resolveCoverUrl(mangaData) {
  const raw = mangaData?.cover_url || mangaData?.cover || mangaData?.cover_image || null;
  if (!raw) return null;
  if (raw.includes('/proxy/image?url=')) return raw;
  if (mangaData?.cover_image || /^https?:\/\//i.test(raw)) {
    return `${API_BASE}/proxy/image?url=${encodeURIComponent(raw)}`;
  }
  return raw;
}

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch (err) {
      console.error("Error parsing watchlist", err);
      return {};
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist));
  }, [watchlist]);

  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === STORAGE_KEY) {
        try {
          setWatchlist(e.newValue ? JSON.parse(e.newValue) : {});
        } catch (err) {
          console.error("Error parsing cross-tab watchlist", err);
        }
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  useEffect(() => {
    const missingCoverTitles = Object.entries(watchlist)
      .filter(([, entry]) => !entry?.cover_url)
      .map(([title]) => title);

    if (missingCoverTitles.length === 0) return;

    let cancelled = false;

    async function hydrateMissingCovers() {
      const updates = await Promise.all(
        missingCoverTitles.map(async (title) => {
          try {
            const res = await fetch(`${API_BASE}/manga/${encodeURIComponent(title)}`);
            if (!res.ok) return null;
            const manga = await res.json();
            const coverUrl = resolveCoverUrl(manga);
            if (!coverUrl) return null;
            return [title, coverUrl];
          } catch {
            return null;
          }
        }),
      );

      if (cancelled) return;

      const validUpdates = updates.filter(Boolean);
      if (validUpdates.length === 0) return;

      setWatchlist((prev) => {
        const next = { ...prev };
        validUpdates.forEach(([title, cover_url]) => {
          if (!next[title]) return;
          next[title] = {
            ...next[title],
            cover_url,
          };
        });
        return next;
      });
    }

    hydrateMissingCovers();

    return () => {
      cancelled = true;
    };
  }, [watchlist]);

  const addOrUpdate = (title, mangaData, status) => {
    const previousStatus = watchlist[title]?.status || null;
    const cover_url = resolveCoverUrl(mangaData);

    setWatchlist(prev => ({
      ...prev,
      [title]: {
        title,
        status,
        cover_url: cover_url || prev[title]?.cover_url || null,
        added_at: prev[title]?.added_at || new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    }));

    if (!previousStatus) {
      trackAnalytics(
        'watchlist_add',
        {
          manga_title: title,
          metadata: {
            status,
          },
        },
        {
          persist: true,
        },
      );
    }
  };

  const remove = (title) => {
    const previousStatus = watchlist[title]?.status || null;
    setWatchlist(prev => {
      const next = { ...prev };
      delete next[title];
      return next;
    });

    if (previousStatus) {
      trackAnalytics(
        'watchlist_remove',
        {
          manga_title: title,
          metadata: {
            from_status: previousStatus,
          },
        },
        {
          persist: true,
        },
      );
    }
  };

  const getStatus = (title) => watchlist[title]?.status || null;

  const STATUSES = ['want_to_read', 'reading', 'completed', 'dropped'];

  const grouped = Object.entries(watchlist).reduce((acc, [title, entry]) => {
    if (!acc[entry.status]) acc[entry.status] = [];
    acc[entry.status].push([title, entry]);
    return acc;
  }, {});

  Object.values(grouped).forEach(list => list.sort((a, b) => new Date(b[1].updated_at) - new Date(a[1].updated_at)));

  const totalCount = Object.keys(watchlist).length;

  return { watchlist, addOrUpdate, remove, getStatus, STATUSES, grouped, totalCount };
}
