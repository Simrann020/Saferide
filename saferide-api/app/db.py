from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

# ---- Connection pool ---------------------------------------------------------

@dataclass
class DBConfig:
    host: str = os.getenv("PGHOST", "localhost")
    port: int = int(os.getenv("PGPORT", "5432"))
    dbname: str = os.getenv("PGDATABASE", "safer_ride")
    user: str = os.getenv("PGUSER", "postgres")
    password: str = os.getenv("PGPASSWORD", "postgres")
    pool_min: int = int(os.getenv("PGPOOL_MIN", "1"))
    pool_max: int = int(os.getenv("PGPOOL_MAX", "10"))

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password}"
        )

cfg = DBConfig()

# Lazy initialization of connection pool
_pool: Optional[ConnectionPool] = None

def get_pool() -> ConnectionPool:
    """Get or create the connection pool (lazy initialization)"""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            cfg.dsn,
            min_size=cfg.pool_min,
            max_size=cfg.pool_max,
            kwargs={"row_factory": dict_row},
        )
    return _pool

def init_database() -> None:
    """Initialize database with PostGIS extension if needed"""
    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                print("🔄 Initializing database...")
                
                # Check if PostGIS is already installed
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_extension WHERE extname = 'postgis'
                    );
                """)
                postgis_exists = cur.fetchone()[0]
                
                if postgis_exists:
                    print("✓ PostGIS extension already installed")
                else:
                    print("📦 Installing PostGIS extension...")
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                        conn.commit()
                        print("✓ PostGIS extension created successfully")
                    except Exception as e:
                        print(f"⚠ Failed to create PostGIS: {e}")
                        conn.rollback()
                        # Try to continue anyway
                
                # Check if our schema exists
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = 'saferide'
                    );
                """)
                schema_exists = cur.fetchone()[0]
                
                if schema_exists:
                    print("✓ saferide schema already exists")
                else:
                    print("📋 Creating saferide schema...")
                    cur.execute("CREATE SCHEMA IF NOT EXISTS saferide;")
                    conn.commit()
                    print("✓ saferide schema created")
                    
    except Exception as e:
        print(f"⚠ Database initialization warning: {e}")
        import traceback
        traceback.print_exc()
        # Don't fail startup if initialization has issues
        pass

# ---- Small helpers -----------------------------------------------------------

def fetchone_value(sql: str, params: tuple[Any, ...]) -> Optional[Any]:
    """
    Execute a single-row SELECT and return the first column (or named 'fc'/'result')
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if not row:
                return None
            # Return a named text/json column if present, else the first value
            if "fc" in row:
                return row["fc"]
            if "result" in row:
                return row["result"]
            return next(iter(row.values())) if row else None

# ---- SQL (psycopg v3 uses %s placeholders) ----------------------------------

# Single z=12 tile as FeatureCollection
SQL_TILE_FC = """
SELECT jsonb_build_object(
  'type','FeatureCollection',
  'features', jsonb_agg(
    jsonb_build_object(
      'type','Feature',
      'properties', jsonb_build_object('x', x, 'y', 'crashes', crashes),
      'geometry', ST_AsGeoJSON(ST_Transform(geom3857, 4326), 6)::jsonb
    )
  )
)::text AS fc
FROM saferide.crash_tiles_z12
WHERE x = %s AND y = %s;
"""

# Top-N tiles as a FeatureCollection
SQL_TOP_FC = """
SELECT jsonb_build_object(
  'type','FeatureCollection',
  'features', jsonb_agg(
    jsonb_build_object(
      'type','Feature',
      'properties', jsonb_build_object('x', x, 'y', y, 'crashes', crashes),
      'geometry', ST_AsGeoJSON(ST_Transform(geom3857, 4326), 6)::jsonb
    )
    ORDER BY crashes DESC
  )
)::text AS fc
FROM (
  SELECT x, y, crashes, geom3857
  FROM saferide.crash_tiles_z12
  ORDER BY crashes DESC
  LIMIT %s
) q;
"""

# Score arbitrary route WKT with buffer (meters)
SQL_SCORE_ROUTE_WKT = """
WITH route AS (
  SELECT ST_SetSRID(ST_GeomFromText(%s), 4326) AS g4326
),
buf AS (
  SELECT ST_Transform(ST_Buffer(ST_Transform(g4326, 3857), %s::double precision), 4326) AS g
  FROM route
),
hits AS (
  SELECT COUNT(*)::int AS crash_count
  FROM saferide.crash c, buf
  WHERE ST_Intersects(c.geom, buf.g)
),
mx AS (
  SELECT COALESCE(MAX(crashes),1) AS max_tile
  FROM saferide.crash_tiles_z12
)
SELECT jsonb_build_object(
  'crashes', hits.crash_count,
  'buffer_m', %s::int,
  'score', LEAST(100, ROUND( 100.0 * LOG(1 + hits.crash_count) / LOG(1 + mx.max_tile) , 2))
)::text AS result
FROM hits, mx;
"""

# Optional: score a bikeway by way_id and buffer (meters)
SQL_SCORE_BIKEWAY = """
WITH bw AS (
  SELECT geom
  FROM saferide.bikeway
  WHERE way_id = %s
),
buf AS (
  SELECT ST_Transform(ST_Buffer(ST_Transform(geom, 3857), %s::double precision), 4326) AS g
  FROM bw
),
hits AS (
  SELECT COUNT(*)::int AS crash_count
  FROM saferide.crash c, buf
  WHERE ST_Intersects(c.geom, buf.g)
),
mx AS (
  SELECT COALESCE(MAX(crashes),1) AS max_tile
  FROM saferide.crash_tiles_z12
)
SELECT jsonb_build_object(
  'way_id', %s,
  'buffer_m', %s::int,
  'crashes', hits.crash_count,
  'score', LEAST(100, ROUND( 100.0 * LOG(1 + hits.crash_count) / LOG(1 + mx.max_tile) , 2))
)::text AS result
FROM hits, mx;
"""
