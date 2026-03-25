-- ============================================================
-- Migration 001: Auth, RLS, and User Watchlists
-- ============================================================
-- Run this in Supabase Dashboard → SQL Editor
-- This must be executed BEFORE deploying the auth-enabled code.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. Create user_watchlists table
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_watchlists (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  manga_title TEXT NOT NULL,
  status     TEXT NOT NULL CHECK (status IN ('want_to_read', 'reading', 'completed', 'dropped')),
  cover_url  TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(user_id, manga_title)
);

-- Index for fast user-scoped queries
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON user_watchlists(user_id);

-- ────────────────────────────────────────────────────────────
-- 2. RLS on user_watchlists — users own their data
-- ────────────────────────────────────────────────────────────

ALTER TABLE user_watchlists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own watchlist"
  ON user_watchlists FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users insert own watchlist"
  ON user_watchlists FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users update own watchlist"
  ON user_watchlists FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users delete own watchlist"
  ON user_watchlists FOR DELETE
  USING (auth.uid() = user_id);

-- ────────────────────────────────────────────────────────────
-- 3. RLS on manga_rankings — public read-only
-- ────────────────────────────────────────────────────────────

ALTER TABLE manga_rankings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read manga_rankings"
  ON manga_rankings FOR SELECT
  USING (true);

-- No INSERT/UPDATE/DELETE policies = only service_role can write

-- ────────────────────────────────────────────────────────────
-- 4. RLS on manga_raw — no public access
-- ────────────────────────────────────────────────────────────

ALTER TABLE manga_raw ENABLE ROW LEVEL SECURITY;

-- No policies = only service_role key can access

-- ────────────────────────────────────────────────────────────
-- 5. RLS on events — anon insert, no read/update/delete
-- ────────────────────────────────────────────────────────────

ALTER TABLE events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can insert events"
  ON events FOR INSERT
  WITH CHECK (true);

-- Optionally: add user_id column to events for future analytics
ALTER TABLE events ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- ────────────────────────────────────────────────────────────
-- 6. Admin role table (simple allowlist)
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS admin_users (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

-- Only service_role can read/write admin_users (no public policies)

-- ────────────────────────────────────────────────────────────
-- 7. Auto-update updated_at trigger for user_watchlists
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_watchlist_updated_at
  BEFORE UPDATE ON user_watchlists
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
