-- ================================
-- Safer Ride: Route Risk Functions
-- ================================

-- Core scorer: takes a 4326 LineString/MultiLineString route, a lookback window,
-- and a neighborhood buffer (meters). It computes crash & hazard densities and
-- returns a JSON payload with a 0–100 risk score plus diagnostics.

CREATE OR REPLACE FUNCTION saferide.score_route(
    route_geom geometry,
    lookback_days integer DEFAULT 365,
    buffer_m double precision DEFAULT 50
) RETURNS jsonb
LANGUAGE sql
AS $$
WITH route AS (
  SELECT ST_LineMerge(ST_CollectionExtract(ST_MakeValid(route_geom), 2)) AS geom
),
len AS (
  -- route length in km; guard against very small/zero to avoid div-by-zero
  SELECT GREATEST(ST_Length((SELECT geom FROM route)::geography)/1000.0, 0.001) AS km
),
cr AS (
  -- crashes within buffer during lookback window
  SELECT
    COALESCE(SUM(
      CASE c.severity
        WHEN 3 THEN 3          -- serious
        WHEN 2 THEN 2          -- injury
        ELSE 1                 -- minor/other
      END
    ), 0) AS crash_weight,
    COUNT(*)::int AS crash_cnt
  FROM saferide.crash c, route r
  WHERE c.occurred_at >= now() - make_interval(days => lookback_days)
    AND ST_DWithin(c.geom::geography, r.geom::geography, buffer_m)
),
hz AS (
  -- “open-ish” hazards near the route
  SELECT COUNT(*)::int AS open_hazards
  FROM saferide.hazard h, route r
  WHERE COALESCE(h.status,'') ILIKE ANY (
          ARRAY['open','re-opened','in_progress','pending_closure','waiting_on_customer','customer_updated']
        )
    AND (h.closed_at IS NULL OR h.closed_at >= now() - make_interval(days => lookback_days))
    AND h.opened_at >= now() - make_interval(days => lookback_days)
    AND ST_DWithin(h.geom::geography, r.geom::geography, buffer_m)
),
dens AS (
  SELECT
    cr.crash_weight / len.km AS crash_weight_per_km,
    cr.crash_cnt    / len.km AS crash_cnt_per_km,
    hz.open_hazards / len.km AS hazard_per_km,
    cr.crash_weight, cr.crash_cnt, hz.open_hazards, len.km
  FROM cr, hz, len
),
scores AS (
  -- Soft-saturating transforms in [0,1); weights: crashes=60, hazards=40
  SELECT
    (1 - exp(-(crash_weight_per_km / 1.5))) * 60.0  AS crash_points,
    (1 - exp(-(hazard_per_km / 3.0)))        * 40.0  AS hazard_points
  FROM dens
)
SELECT jsonb_build_object(
  'params',        jsonb_build_object('lookback_days', lookback_days, 'buffer_m', buffer_m),
  'length_km',     (SELECT km FROM dens),
  'counts',        jsonb_build_object('crashes', (SELECT crash_cnt FROM dens),
                                      'crash_weight', (SELECT crash_weight FROM dens),
                                      'open_hazards', (SELECT open_hazards FROM dens)),
  'densities',     jsonb_build_object('crash_cnt_per_km', (SELECT crash_cnt_per_km FROM dens),
                                      'crash_weight_per_km', (SELECT crash_weight_per_km FROM dens),
                                      'hazard_per_km', (SELECT hazard_per_km FROM dens)),
  'component_pts', jsonb_build_object('crash_points', (SELECT crash_points FROM scores),
                                      'hazard_points', (SELECT hazard_points FROM scores)),
  'score',         CEIL(LEAST( (SELECT crash_points + hazard_points FROM scores), 100.0))::int
);
$$;

-- WKT convenience wrapper
CREATE OR REPLACE FUNCTION saferide.score_route_wkt(
    route_wkt text,
    lookback_days integer DEFAULT 365,
    buffer_m double precision DEFAULT 50
) RETURNS jsonb
LANGUAGE sql
AS $$
  SELECT saferide.score_route(ST_GeomFromText(route_wkt, 4326), lookback_days, buffer_m);
$$;

-- Score a stored bikeway segment by primary key (infra_id)
CREATE OR REPLACE FUNCTION saferide.score_bikeway_segment(
    p_infra_id text,
    lookback_days integer DEFAULT 365,
    buffer_m double precision DEFAULT 50
) RETURNS jsonb
LANGUAGE sql
AS $$
  SELECT saferide.score_route(b.geom, lookback_days, buffer_m)
  FROM saferide.bikeway b
  WHERE b.infra_id = p_infra_id;
$$;
