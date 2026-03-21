ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS count_current integer DEFAULT 0;
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS count_completed integer DEFAULT 0;
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS count_dropped integer DEFAULT 0;
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS count_paused integer DEFAULT 0;
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS count_planning integer DEFAULT 0;
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS external_id text;
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS mal_cross_id text;
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS alt_titles text[];
ALTER TABLE manga_raw ADD COLUMN IF NOT EXISTS cross_link_ids text[];

ALTER TABLE manga_rankings
  ADD COLUMN IF NOT EXISTS completion_rate float DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS total_readers   integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS alt_titles      text[];
