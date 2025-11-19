-- Compute slippy-tile x/y for a geometry at zoom z (assumes geom in 4326)
CREATE OR REPLACE FUNCTION st_tilecoord(z integer, g geometry)
RETURNS TABLE(x int, y int)
LANGUAGE sql
IMMUTABLE
AS $$
  WITH p AS (
    -- use a point; crashes are points. If not, use ST_PointOnSurface(g)
    SELECT ST_Transform(g, 3857) AS m
  ),
  t AS (
    SELECT
      40075016.6855784 / (2^z)::float8 AS tile_size,  -- meters per tile
      20037508.3427892 AS origin                       -- WebMercator origin
  )
  SELECT
    floor( (ST_X(p.m) + t.origin) / t.tile_size )::int AS x,
    floor( (t.origin - ST_Y(p.m)) / t.tile_size )::int AS y
  FROM p, t;
$$;
