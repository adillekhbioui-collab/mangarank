import { useCallback } from 'react';
import { logEvent } from '../utils/logEvent.js';

export function trackAnalytics(eventName, eventData = {}, { persist = false } = {}) {
  if (typeof window !== 'undefined' && window.umami?.track) {
    window.umami.track(eventName, eventData);
  }

  if (persist) {
    logEvent(eventName, eventData);
  }
}

export function useAnalytics() {
  const track = useCallback((eventName, eventData = {}, options = {}) => {
    trackAnalytics(eventName, eventData, options);
  }, []);

  return { track };
}
