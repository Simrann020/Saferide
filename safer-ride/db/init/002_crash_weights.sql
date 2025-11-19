-- 002_crash_weights.sql
-- Create a view with severity+recency weights for each crash

-- NOTE: change table name below if your table is saferide.crashes (plural)

CREATE OR REPLACE VIEW saferide.crash_weights AS
SELECT
  c.crash_id,
  c.severity,
  c.occurred_at,
  c.geom,
  (CASE c.severity
     WHEN 4 THEN 1.00   -- fatal
     WHEN 3 THEN 0.60   -- serious injury
     WHEN 2 THEN 0.30   -- minor injury
     ELSE 0.10          -- property damage only / unknown
   END) AS sev_w,
  EXTRACT(EPOCH FROM (NOW() - c.occurred_at)) / (30*24*3600.0) AS age_months,
  EXP( - LN(2) * (EXTRACT(EPOCH FROM (NOW() - c.occurred_at)) / (30*24*3600.0)) / 24.0 ) AS rec_w,
  (CASE c.severity
     WHEN 4 THEN 1.00
     WHEN 3 THEN 0.60
     WHEN 2 THEN 0.30
     ELSE 0.10
   END)
  * EXP( - LN(2) * (EXTRACT(EPOCH FROM (NOW() - c.occurred_at)) / (30*24*3600.0)) / 24.0 ) AS weight
FROM saferide.crash c;

-- Helpful indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_crash_geom_4326 ON saferide.crash USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_crash_occurred_at ON saferide.crash(occurred_at);
CREATE INDEX IF NOT EXISTS idx_crash_severity ON saferide.crash(severity);
