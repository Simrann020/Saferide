-- Create app schema and user (safe if re-run)
CREATE SCHEMA IF NOT EXISTS saferide;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'saferide_app') THEN
    CREATE ROLE saferide_app WITH LOGIN PASSWORD 'saferide_app_pwd';
  END IF;
END$$;

-- Set search path for this session/file
SET search_path TO saferide, public;

-- ===== Tables =====

-- Bikeways (lines)
CREATE TABLE IF NOT EXISTS bikeway (
  infra_id   TEXT PRIMARY KEY,
  class      TEXT,  -- protected, buffered, painted, shared, trail, unpaved
  on_off     TEXT,  -- ON-STREET / OFF-STREET / NOT APPLICABLE
  status     TEXT,  -- EXISTING / PROPOSED / UNKNOWN
  geom       geometry(MULTILINESTRING, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS bikeway_gix ON bikeway USING GIST (geom);

-- 311 Hazards (points)
CREATE TABLE IF NOT EXISTS hazard (
  hazard_id  TEXT PRIMARY KEY,
  category   TEXT,        -- pothole, debris, signal, other
  status     TEXT,        -- open, in_progress, closed
  opened_at  TIMESTAMP,
  closed_at  TIMESTAMP,
  geom       geometry(POINT, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS hazard_gix ON hazard USING GIST (geom);
CREATE INDEX IF NOT EXISTS hazard_opened_ix ON hazard (opened_at);

-- Crashes (points)
CREATE TABLE IF NOT EXISTS crash (
  crash_id    TEXT PRIMARY KEY,
  occurred_at TIMESTAMP,
  severity    SMALLINT,   -- 1=fatal, 2=serious, 3=minor (MVP mapping)
  geom        geometry(POINT, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS crash_gix ON crash USING GIST (geom);
CREATE INDEX IF NOT EXISTS crash_time_ix ON crash (occurred_at);

-- Optional: user routes for alerts (lines)
CREATE TABLE IF NOT EXISTS user_route (
  user_id     TEXT,
  route_id    TEXT,
  name        TEXT,
  created_at  TIMESTAMP DEFAULT now(),
  geom        geometry(MULTILINESTRING, 4326) NOT NULL,
  PRIMARY KEY (user_id, route_id)
);
CREATE INDEX IF NOT EXISTS user_route_gix ON user_route USING GIST (geom);

-- ===== Grants for app user =====
GRANT USAGE ON SCHEMA saferide TO saferide_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA saferide TO saferide_app;

-- ensure future tables get the same grants
ALTER DEFAULT PRIVILEGES IN SCHEMA saferide
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO saferide_app;
