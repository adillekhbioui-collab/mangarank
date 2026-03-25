import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE } from '../api';
import { trackAnalytics } from './useAnalytics.js';
import { supabase } from '../lib/supabaseClient';
import { useAuth } from '../contexts/AuthContext';

const STORAGE_KEY = 'manga_watchlist';
const MERGE_DONE_KEY = 'manga_watchlist_merged';

function resolveCoverUrl(mangaData) {
  const raw = mangaData?.cover_url || mangaData?.cover || mangaData?.cover_image || null;
  if (!raw) return null;
  if (raw.includes('/proxy/image?url=')) return raw;
  if (mangaData?.cover_image || /^https?:\/\//i.test(raw)) {
    return `${API_BASE}/proxy/image?url=${encodeURIComponent(raw)}`;
  }
  return raw;
}

/* Read localStorage once, safely */
function readLocal() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
}

/* Write to localStorage */
function writeLocal(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch { /* quota exceeded – silently ignore */ }
}

export function useWatchlist() {
  const { user } = useAuth();

  // Always initialise from localStorage so we never start empty
  const [watchlist, setWatchlist] = useState(readLocal);
  const [cloudReady, setCloudReady] = useState(false);
  const mergeAttempted = useRef(false);

  // ── 1. CLOUD LOAD ────────────────────────────────────────────
  // When a user is logged in, try to load their cloud watchlist.
  // If Supabase returns data we replace the local state.
  // If the fetch fails (table missing, RLS, network), we keep localStorage data.
  useEffect(() => {
    if (!user) {
      setCloudReady(false);
      return;
    }

    let active = true;

    (async () => {
      try {
        const { data, error } = await supabase
          .from('user_watchlists')
          .select('*');

        if (error) throw error;
        if (!active) return;

        // Only replace if the cloud actually has rows
        if (data && data.length > 0) {
          const cloud = {};
          for (const row of data) {
            cloud[row.manga_title] = {
              title: row.manga_title,
              status: row.status,
              cover_url: row.cover_url,
              added_at: row.created_at,
              updated_at: row.updated_at,
            };
          }
          setWatchlist(cloud);
          writeLocal(cloud); // keep localStorage in sync as backup
        }
        setCloudReady(true);
      } catch (err) {
        console.warn('Cloud watchlist load failed – using localStorage', err);
        setCloudReady(false);
      }
    })();

    return () => { active = false; };
  }, [user]);

  // ── 2. MERGE LOCAL → CLOUD (once per account) ────────────────
  useEffect(() => {
    if (!user || !cloudReady || mergeAttempted.current) return;

    // Use localStorage flag so we never ask twice, even across page reloads
    const alreadyMerged = localStorage.getItem(MERGE_DONE_KEY);
    if (alreadyMerged) {
      mergeAttempted.current = true;
      return;
    }

    mergeAttempted.current = true;

    const localData = readLocal();
    const titles = Object.keys(localData);
    if (titles.length === 0) {
      // Nothing to merge — mark done so we never ask
      localStorage.setItem(MERGE_DONE_KEY, 'true');
      return;
    }

    // Mark done IMMEDIATELY so no re-mount / strict-mode replay can re-trigger
    localStorage.setItem(MERGE_DONE_KEY, 'true');

    // Use setTimeout so the React render finishes before the blocking dialog
    setTimeout(async () => {
      const accepted = window.confirm(
        `You have ${titles.length} title${titles.length > 1 ? 's' : ''} in your local offline watchlist. Import them to your account?`
      );

      if (!accepted) return; // user cancelled — nothing to do

      try {
        const payload = titles.map(t => ({
          user_id: user.id,
          manga_title: t,
          status: localData[t].status || 'want_to_read',
          cover_url: localData[t].cover_url || null,
        }));

        const { error } = await supabase
          .from('user_watchlists')
          .upsert(payload, { onConflict: 'user_id,manga_title' });

        if (error) throw error;

        // Re-fetch from cloud to get authoritative state
        const { data } = await supabase.from('user_watchlists').select('*');
        if (data) {
          const merged = {};
          for (const row of data) {
            merged[row.manga_title] = {
              title: row.manga_title,
              status: row.status,
              cover_url: row.cover_url,
              added_at: row.created_at,
              updated_at: row.updated_at,
            };
          }
          setWatchlist(merged);
          writeLocal(merged);
        }
      } catch (err) {
        console.error('Merge failed', err);
      }
    }, 500);
  }, [user, cloudReady]);

  // ── 3. PERSIST EVERY CHANGE TO LOCALSTORAGE ──────────────────
  // This is the critical fix: ALWAYS write to localStorage on every change,
  // regardless of login state. This ensures data survives page reloads
  // even if the Supabase write silently fails.
  useEffect(() => {
    writeLocal(watchlist);
  }, [watchlist]);

  // Cross-tab sync (only matters for logged-out browsing)
  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === STORAGE_KEY) {
        try {
          setWatchlist(e.newValue ? JSON.parse(e.newValue) : {});
        } catch { /* ignore */ }
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  // ── 4. COVER HYDRATION ───────────────────────────────────────
  useEffect(() => {
    const missing = Object.entries(watchlist)
      .filter(([, e]) => !e?.cover_url)
      .map(([t]) => t);

    if (missing.length === 0) return;
    let cancelled = false;

    (async () => {
      const updates = await Promise.all(
        missing.map(async (title) => {
          try {
            const res = await fetch(`${API_BASE}/manga/${encodeURIComponent(title)}`);
            if (!res.ok) return null;
            const manga = await res.json();
            const coverUrl = resolveCoverUrl(manga);
            return coverUrl ? [title, coverUrl] : null;
          } catch { return null; }
        })
      );

      if (cancelled) return;
      const valid = updates.filter(Boolean);
      if (valid.length === 0) return;

      setWatchlist(prev => {
        const next = { ...prev };
        valid.forEach(([title, cover_url]) => {
          if (next[title]) next[title] = { ...next[title], cover_url };
        });
        return next;
      });

      // Sync covers to cloud too
      if (user) {
        const dbUpdates = valid.map(([title, cover_url]) => ({
          user_id: user.id,
          manga_title: title,
          status: watchlist[title]?.status || 'want_to_read',
          cover_url,
        }));
        supabase.from('user_watchlists').upsert(dbUpdates, { onConflict: 'user_id,manga_title' }).then();
      }
    })();

    return () => { cancelled = true; };
  }, [watchlist, user]);

  // ── 5. MUTATIONS ─────────────────────────────────────────────
  const addOrUpdate = useCallback(async (title, mangaData, status) => {
    const cover_url = resolveCoverUrl(mangaData);
    const now = new Date().toISOString();

    setWatchlist(prev => {
      const previousStatus = prev[title]?.status || null;

      // Fire analytics only on first add
      if (!previousStatus) {
        trackAnalytics('watchlist_add', { manga_title: title, metadata: { status } }, { persist: true });
      }

      const entry = {
        title,
        status,
        cover_url: cover_url || prev[title]?.cover_url || null,
        added_at: prev[title]?.added_at || now,
        updated_at: now,
      };

      return { ...prev, [title]: entry };
    });

    // Cloud sync
    if (user) {
      try {
        await supabase.from('user_watchlists').upsert({
          user_id: user.id,
          manga_title: title,
          status,
          cover_url: cover_url || null,
        }, { onConflict: 'user_id,manga_title' });
      } catch (err) {
        console.error('Cloud sync failed for add', err);
      }
    }
  }, [user]);

  const remove = useCallback(async (title) => {
    setWatchlist(prev => {
      const previousStatus = prev[title]?.status;
      if (previousStatus) {
        trackAnalytics('watchlist_remove', { manga_title: title, metadata: { from_status: previousStatus } }, { persist: true });
      }
      const next = { ...prev };
      delete next[title];
      return next;
    });

    if (user) {
      try {
        await supabase.from('user_watchlists').delete().eq('manga_title', title).eq('user_id', user.id);
      } catch (err) {
        console.error('Cloud sync failed for remove', err);
      }
    }
  }, [user]);

  // ── 6. DERIVED DATA ──────────────────────────────────────────
  const getStatus = useCallback((title) => watchlist[title]?.status || null, [watchlist]);

  const STATUSES = ['want_to_read', 'reading', 'completed', 'dropped'];

  const grouped = Object.entries(watchlist).reduce((acc, [title, entry]) => {
    if (!acc[entry.status]) acc[entry.status] = [];
    acc[entry.status].push([title, entry]);
    return acc;
  }, {});

  Object.values(grouped).forEach(list =>
    list.sort((a, b) => new Date(b[1].updated_at) - new Date(a[1].updated_at))
  );

  const totalCount = Object.keys(watchlist).length;

  return { watchlist, addOrUpdate, remove, getStatus, STATUSES, grouped, totalCount };
}
