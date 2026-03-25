/**
 * Supabase browser client — uses the ANON key only.
 * Never import or reference the service_role key in frontend code.
 *
 * Gracefully handles missing env vars so the app still renders
 * (auth features just won't work).
 */
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    '[supabaseClient] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY env vars. Auth features will be disabled.',
  );
}

// Create a real client if keys are present, otherwise a dummy placeholder
// that won't crash the app. Auth calls will simply return errors.
export const supabase = (supabaseUrl && supabaseAnonKey)
  ? createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
    },
  })
  : createClient('https://placeholder.supabase.co', 'placeholder-key-that-will-fail-auth', {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
      detectSessionInUrl: false,
    },
  });
