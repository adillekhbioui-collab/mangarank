import { API_BASE } from '../api.js';
import { getSessionId } from './session.js';
import { supabase } from '../lib/supabaseClient.js';

const PERSISTED_EVENTS = new Set([
  'search',
  'manga_click',
  'manga_view',
  'filter_applied',
  'watchlist_add',
  'watchlist_remove',
]);

export async function logEvent(eventType, data = {}) {
  if (!PERSISTED_EVENTS.has(eventType)) return;

  // Attach user_id if logged in (non-blocking)
  let userId = null;
  try {
    const { data: { session } } = await supabase.auth.getSession();
    userId = session?.user?.id ?? null;
  } catch {
    // Auth not available — continue without user_id
  }

  try {
    await fetch(`${API_BASE}/analytics/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        event_type: eventType,
        session_id: getSessionId(),
        user_id: userId,
        manga_title: data.manga_title || null,
        genre: data.genre || null,
        filter_state: data.filter_state || null,
        metadata: data.metadata || null,
      }),
    });
  } catch {
    // Analytics should never break user interactions.
  }
}

