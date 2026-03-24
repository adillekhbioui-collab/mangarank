import { API_BASE } from '../api.js';
import { getSessionId } from './session.js';

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

  try {
    await fetch(`${API_BASE}/analytics/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        event_type: eventType,
        session_id: getSessionId(),
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
