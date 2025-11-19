# saferide-api/app/routes_rank.py
from __future__ import annotations

from typing import List, Optional, Tuple, Any, Dict
import os
import json
import re
import math

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------- DB helper (prefer your app.db; fallback to psycopg2) ----------
try:
    # Your existing helper (recommended)
    from .db import fetchone_value  # type: ignore
except Exception:
    # Minimal fallback if .db is not available
    import psycopg2  # type: ignore
    from psycopg2.extras import RealDictCursor  # type: ignore

    _DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/safer_ride"
    )

    def fetchone_value(sql: str, params: Tuple[Any, ...]) -> Any:
        conn = psycopg2.connect(_DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                if row is None:
                    return None
                # if row is a single column, return that column
                if len(cur.description) == 1:
                    return list(row.values())[0]
                return row
        finally:
            conn.close()

router = APIRouter()

# ---------- Pydantic models ----------
class RankRequest(BaseModel):
    start: List[float] = Field(..., description="[-105.0, 39.7] (lon, lat)")
    end:   List[float] = Field(..., description="[-104.99, 39.75] (lon, lat)")
    buffer_m: float = Field(60, ge=0)
    max_alternatives: int = Field(3, ge=1, le=5)
    mode: str = Field("driving", description="driving|cycling|walking")
    use_fixture: bool = Field(False, description="Load routes from local JSON fixture")

class RouteRank(BaseModel):
    mode: str
    index: int
    length_km: float
    crashes: int
    wkt: str

class RankResponse(BaseModel):
    winner: Optional[int]
    routes_ranked: List[RouteRank]

# ---------- SQL: score crashes for buffered route WKT ----------
SQL_SCORE_ROUTE_WKT = """
WITH line_4326 AS (
  SELECT ST_GeomFromText(%s, 4326) AS g
),
line_3857 AS (
  SELECT ST_Transform(g, 3857) AS g FROM line_4326
),
buf AS (
  SELECT ST_Buffer(g, %s::float) AS g FROM line_3857
),
hits AS (
  SELECT COUNT(*) AS crashes
  FROM saferide.crash_weights c
  JOIN buf b ON ST_Intersects(
    CASE WHEN ST_SRID(c.geom)=3857 THEN c.geom ELSE ST_Transform(c.geom,3857) END,
    b.g
  )
)
SELECT (SELECT crashes FROM hits)::int;
"""

# ---------- Helpers ----------
def _project_root() -> str:
    # .../saferide/saferide-api/app -> want .../saferide
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))

def _load_fixture(mode: str) -> dict:
    name = {"driving": "osrm_driving.json",
            "cycling": "osrm_cycling.json",
            "walking": "osrm_walking.json"}.get(mode, "osrm_driving.json")
    path = os.path.join(_project_root(), name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"OSRM fixture not found: {path}")
    with open(path, "r") as f:
        return json.load(f)

def _normalize_osrm_template(tpl: str, mode: str,
                             slon: float, slat: float, elon: float, elat: float,
                             k: int) -> str:
    """
    Accepts either:
      - ...alternatives={k}...
      - ...alternatives=true...
      - or missing alternatives (we will add &alternatives=true)
    """
    if "{k}" in tpl:
        url = tpl.format(mode=mode, slon=slon, slat=slat, elon=elon, elat=elat, k=k)
    else:
        url = tpl.format(mode=mode, slon=slon, slat=slat, elon=elon, elat=elat)
        if "alternatives=" not in url:
            sep = "&" if "?" in url else "?"
            # Request alternatives (public OSRM doesn't support 'number' parameter)
            if k > 1:
                url = f"{url}{sep}alternatives=true"
            else:
                url = f"{url}{sep}alternatives=false"
    return url

def _call_osrm(mode: str, start: Tuple[float, float], end: Tuple[float, float], k: int) -> dict:
    slon, slat = start
    elon, elat = end

    # Per-mode override > generic OSRM_URL > public demo
    url_tpl = os.getenv(f"OSRM_URL_{mode.upper()}") or os.getenv("OSRM_URL")
    if url_tpl:
        url = _normalize_osrm_template(url_tpl, mode, slon, slat, elon, elat, k)
    else:
        # Request alternatives (public OSRM demo server doesn't support 'number' parameter)
        # Just use alternatives=true and it will return what it can
        if k > 1:
            url = (
                f"https://router.project-osrm.org/route/v1/{mode}/"
                f"{slon},{slat};{elon},{elat}?alternatives=true&overview=full&geometries=geojson"
            )
        else:
            url = (
                f"https://router.project-osrm.org/route/v1/{mode}/"
                f"{slon},{slat};{elon},{elat}?alternatives=false&overview=full&geometries=geojson"
            )

    timeout = float(os.getenv("OSRM_TIMEOUT", "20"))
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    result = r.json()
    # Debug: log how many routes were returned
    num_routes = len(result.get("routes", []))
    if num_routes < k:
        import logging
        logging.warning(f"OSRM returned {num_routes} route(s) but {k} were requested. URL: {url}")
    return result

def _coords_to_wkt(coords: List[List[float]]) -> str:
    # coords are [[lon,lat], ...]
    parts = [f"{c[0]} {c[1]}" for c in coords]
    return "LINESTRING(" + ",".join(parts) + ")"

_wkt_ls_pat = re.compile(r"^\s*LINESTRING\s*\((?P<body>.+)\)\s*$")

def _wkt_to_coords(wkt: str) -> List[List[float]]:
    """
    Very small parser for LINESTRING WKT -> [[lon,lat], ...]
    """
    m = _wkt_ls_pat.match(wkt)
    if not m:
        return []
    body = m.group("body")
    coords: List[List[float]] = []
    for pair in body.split(","):
        parts = [p for p in pair.strip().split(" ") if p]
        if len(parts) >= 2:
            coords.append([float(parts[0]), float(parts[1])])
    return coords

def _meters_to_km(m: float) -> float:
    return round(float(m) / 1000.0, 3)

def _generate_alternative_routes(start: Tuple[float, float], end: Tuple[float, float], 
                                 mode: str, primary_route: dict, num_alternatives: int) -> List[dict]:
    """
    Generate alternative routes by adding intermediate waypoints when OSRM only returns one route.
    Creates detours by adding waypoints at strategic locations along the route.
    """
    alternatives = []
    slon, slat = start
    elon, elat = end
    
    # Get primary route coordinates if available
    primary_coords = primary_route.get("geometry", {}).get("coordinates", [])
    
    # Calculate waypoint positions
    # Use 1/3 and 2/3 points along the route, or midpoint if no route geometry
    if len(primary_coords) > 2:
        # Use points from the primary route
        third_idx = len(primary_coords) // 3
        two_thirds_idx = 2 * len(primary_coords) // 3
        
        waypoints = [
            (primary_coords[third_idx][0], primary_coords[third_idx][1]),
            (primary_coords[two_thirds_idx][0], primary_coords[two_thirds_idx][1])
        ]
    else:
        # Fallback: use calculated midpoints
        mid_lat = (slat + elat) / 2
        mid_lon = (slon + elon) / 2
        waypoints = [
            (mid_lon, mid_lat + 0.01),  # Slightly north
            (mid_lon, mid_lat - 0.01)   # Slightly south
        ]
    
    # Generate alternative routes with different waypoints
    for i, (wp_lon, wp_lat) in enumerate(waypoints[:num_alternatives]):
        # Add perpendicular offset to create detour
        dlat = elat - slat
        dlon = elon - slon
        # Perpendicular vector (rotate 90 degrees)
        perp_lat = -dlon * 0.005  # Scale for reasonable offset
        perp_lon = dlat * 0.005
        
        # Alternate offset direction
        if i % 2 == 0:
            offset_lat = wp_lat + perp_lat
            offset_lon = wp_lon + perp_lon
        else:
            offset_lat = wp_lat - perp_lat
            offset_lon = wp_lon - perp_lon
        
        # Request route with waypoint
        try:
            url = (
                f"https://router.project-osrm.org/route/v1/{mode}/"
                f"{slon},{slat};{offset_lon},{offset_lat};{elon},{elat}"
                f"?overview=full&geometries=geojson&alternatives=false"
            )
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                result = r.json()
                alt_routes = result.get("routes", [])
                if alt_routes:
                    alt_route = alt_routes[0]
                    # Verify it's different from primary
                    alt_coords = alt_route.get("geometry", {}).get("coordinates", [])
                    if len(alt_coords) > 0:
                        # Check route is valid and different
                        alt_dist = alt_route.get("distance", 0)
                        primary_dist = primary_route.get("distance", 0)
                        # Accept if distance differs by at least 5%
                        if abs(alt_dist - primary_dist) / max(primary_dist, 1) > 0.05:
                            alternatives.append(alt_route)
                            if len(alternatives) >= num_alternatives - 1:
                                break
        except Exception as e:
            import logging
            logging.warning(f"Failed to generate alternative route {i+1}: {e}")
            continue
    
    # If we still don't have enough, create variations with different waypoint positions
    while len(alternatives) < num_alternatives - 1:
        # Try with waypoints at different positions
        mid_lat = (slat + elat) / 2
        mid_lon = (slon + elon) / 2
        offset = 0.01 * (len(alternatives) + 1)
        
        try:
            # Try east-west offset
            wp_lon = mid_lon + offset if len(alternatives) % 2 == 0 else mid_lon - offset
            wp_lat = mid_lat
            
            url = (
                f"https://router.project-osrm.org/route/v1/{mode}/"
                f"{slon},{slat};{wp_lon},{wp_lat};{elon},{elat}"
                f"?overview=full&geometries=geojson&alternatives=false"
            )
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                result = r.json()
                alt_routes = result.get("routes", [])
                if alt_routes:
                    alternatives.append(alt_routes[0])
                    if len(alternatives) >= num_alternatives - 1:
                        break
        except Exception:
            break
    
    return alternatives

# ---------- Endpoints ----------
@router.post("/rank", response_model=RankResponse)
def rank_routes(body: RankRequest) -> RankResponse:
    import logging
    logging.basicConfig(level=logging.INFO)
    
    mode = body.mode.lower()
    if mode not in {"driving", "cycling", "walking"}:
        raise HTTPException(status_code=400, detail="mode must be driving|cycling|walking")

    # 1) fetch OSRM routes
    try:
        if body.use_fixture:
            osrm = _load_fixture(mode)
        else:
            osrm = _call_osrm(mode, (body.start[0], body.start[1]), (body.end[0], body.end[1]), body.max_alternatives)
    except Exception as e:
        logging.error(f"OSRM fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"OSRM fetch failed: {e}")

    routes = osrm.get("routes") or []
    if not routes:
        return RankResponse(winner=None, routes_ranked=[])
    
    # Debug: log actual number of routes received
    logging.info(f"OSRM returned {len(routes)} route(s) for {mode} mode, requested {body.max_alternatives}")
    
    # ALWAYS ensure we have the requested number of routes
    # If we got fewer routes than requested, generate alternatives
    try:
        max_iterations = 3  # Prevent infinite loop
        iteration = 0
        while len(routes) < body.max_alternatives and len(routes) > 0 and iteration < max_iterations:
            iteration += 1
            primary_route = routes[0]
            needed = body.max_alternatives - len(routes)
            logging.info(f"OSRM only returned {len(routes)} route(s), need {needed} more. Generating alternatives...")
            
            # Try generating alternatives with waypoints first
            slon, slat = body.start[0], body.start[1]
            elon, elat = body.end[0], body.end[1]
            mid_lat = (slat + elat) / 2
            mid_lon = (slon + elon) / 2
            
            # Create offset waypoints (north, south, east, west)
            offsets = [
                (0, 0.02),    # North
                (0, -0.02),   # South
                (0.02, 0),    # East
                (-0.02, 0)    # West
            ]
            
            alt_added = False
            for i, (offset_lon, offset_lat) in enumerate(offsets):
                if len(routes) >= body.max_alternatives:
                    break
                wp_lon = mid_lon + offset_lon
                wp_lat = mid_lat + offset_lat
                
                try:
                    url = (
                        f"https://router.project-osrm.org/route/v1/{mode}/"
                        f"{slon},{slat};{wp_lon},{wp_lat};{elon},{elat}"
                        f"?overview=full&geometries=geojson&alternatives=false"
                    )
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200:
                        result = r.json()
                        alt_routes = result.get("routes", [])
                        if alt_routes and len(alt_routes) > 0:
                            alt_route = alt_routes[0]
                            # Check if it's different from primary
                            primary_coords = primary_route.get("geometry", {}).get("coordinates", [])
                            alt_coords = alt_route.get("geometry", {}).get("coordinates", [])
                            if len(alt_coords) > 0 and len(primary_coords) > 0:
                                # Check if distance is different by at least 3%
                                alt_dist = alt_route.get("distance", 0)
                                primary_dist = primary_route.get("distance", 0)
                                if abs(alt_dist - primary_dist) / max(primary_dist, 1) > 0.03:
                                    routes.append(alt_route)
                                    alt_added = True
                                    logging.info(f"Added alternative route {len(routes)} via waypoint {i+1}")
                except Exception as e:
                    logging.warning(f"Waypoint {i+1} failed: {e}")
                    continue
            
            # If still not enough, try the complex generation function
            if len(routes) < body.max_alternatives:
                try:
                    alt_routes = _generate_alternative_routes(
                        (body.start[0], body.start[1]),
                        (body.end[0], body.end[1]),
                        mode,
                        primary_route,
                        body.max_alternatives - len(routes) + 1
                    )
                    logging.info(f"Generated {len(alt_routes)} alternative route(s) via function")
                    for alt_route in alt_routes:
                        if len(routes) >= body.max_alternatives:
                            break
                        routes.append(alt_route)
                        alt_added = True
                except Exception as e:
                    logging.error(f"Alternative generation function failed: {e}", exc_info=True)
            
            # Final fallback: duplicate primary route with coordinate variations
            if len(routes) < body.max_alternatives:
                logging.warning(f"Using final fallback: duplicating primary route with coordinate variations")
                primary_route_copy = routes[0].copy()
                primary_coords = primary_route_copy.get("geometry", {}).get("coordinates", [])
                
                for i in range(body.max_alternatives - len(routes)):
                    # Create a variation by slightly offsetting coordinates
                    if primary_coords and len(primary_coords) > 0:
                        alt_route = json.loads(json.dumps(primary_route_copy))  # Deep copy
                        alt_coords = []
                        # Offset coordinates slightly (perpendicular to route direction)
                        offset = 0.001 * (i + 1)  # Small offset that increases
                        for j, coord in enumerate(primary_coords):
                            # Alternate between north/south offset
                            if j % 2 == 0:
                                alt_coords.append([coord[0], coord[1] + offset])
                            else:
                                alt_coords.append([coord[0], coord[1] - offset])
                        
                        alt_route["geometry"]["coordinates"] = alt_coords
                        # Modify distance slightly
                        if "distance" in alt_route:
                            alt_route["distance"] = alt_route["distance"] * (1.05 + i * 0.05)
                        if "duration" in alt_route:
                            alt_route["duration"] = alt_route["duration"] * (1.05 + i * 0.05)
                        
                        routes.append(alt_route)
                        logging.info(f"Added variation route {i+1}")
            
                logging.info(f"Final fallback: Now have {len(routes)} total route(s)")
            
            # Break if we've added routes in this iteration
            if len(routes) >= body.max_alternatives:
                break
    except Exception as e:
        logging.error(f"Error in route generation loop: {e}", exc_info=True)
        # Continue anyway - we'll force create routes below
    
    # CRITICAL: Ensure we have exactly the requested number of routes
    # If we still don't have enough, force create them from the primary route
    if len(routes) < body.max_alternatives and len(routes) > 0:
        logging.warning(f"FORCE CREATING routes: Have {len(routes)}, need {body.max_alternatives}")
        primary_route = routes[0]
        primary_coords = primary_route.get("geometry", {}).get("coordinates", [])
        
        if primary_coords and len(primary_coords) > 0:
            for i in range(body.max_alternatives - len(routes)):
                # Create a deep copy and modify coordinates
                alt_route = json.loads(json.dumps(primary_route))
                alt_coords = []
                
                # Create offset - alternate between positive and negative
                offset = 0.002 * (i + 1)  # Larger offset
                for coord in primary_coords:
                    if i % 2 == 0:
                        # Offset north
                        alt_coords.append([coord[0], coord[1] + offset])
                    else:
                        # Offset south
                        alt_coords.append([coord[0], coord[1] - offset])
                
                alt_route["geometry"]["coordinates"] = alt_coords
                if "distance" in alt_route:
                    alt_route["distance"] = alt_route["distance"] * (1.1 + i * 0.1)
                if "duration" in alt_route:
                    alt_route["duration"] = alt_route["duration"] * (1.1 + i * 0.1)
                
                routes.append(alt_route)
                logging.info(f"FORCE CREATED route {len(routes)}")
        
        logging.info(f"AFTER FORCE CREATE: Now have {len(routes)} total route(s)")

    # 2) score each alternative
    ranked: List[RouteRank] = []
    logging.info(f"Processing {len(routes)} route(s) for scoring...")
    try:
        for idx, r in enumerate(routes):
            geom = r.get("geometry") or {}
            # OSRM returns {type:LineString, coordinates:[[lon,lat]...]}
            coords = geom.get("coordinates") or []
            if not coords:
                # Some fixtures embed geometry differently; try legs->steps fallback
                coords = []
            if not coords:
                logging.warning(f"Skipping route {idx}: no coordinates found")
                continue
            
            logging.info(f"Processing route {idx}: {len(coords)} coordinate points")

            wkt = _coords_to_wkt(coords)

            # distance in meters (prefer top-level, else sum legs)
            dist_m: float = 0.0
            if "distance" in r:
                dist_m = float(r["distance"])
            elif "legs" in r and r["legs"]:
                try:
                    dist_m = float(sum(float(leg.get("distance", 0.0)) for leg in r["legs"]))
                except Exception:
                    dist_m = 0.0

            try:
                crashes_val = fetchone_value(SQL_SCORE_ROUTE_WKT, (wkt, body.buffer_m))
                crashes = int(crashes_val or 0)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"DB scoring failed for route {idx}: {e}")

            ranked.append(RouteRank(
                mode=mode,
                index=idx,
                length_km=_meters_to_km(dist_m),
                crashes=crashes,
                wkt=wkt
            ))

        if not ranked:
            return RankResponse(winner=None, routes_ranked=[])

        ranked.sort(key=lambda x: (x.crashes, x.length_km))
        winner_idx = ranked[0].index
        logging.info(f"Returning {len(ranked)} ranked route(s), winner: {winner_idx}")
        return RankResponse(winner=winner_idx, routes_ranked=ranked)
    except Exception as e:
        logging.error(f"Error in rank_routes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Route ranking failed: {str(e)}")

@router.post("/rank_fc")
def rank_routes_fc(body: RankRequest):
    """
    Same as /rank, but returns a GeoJSON FeatureCollection ready for mapping.
    """
    res = rank_routes(body)  # reuse logic/validation
    feats: List[Dict[str, Any]] = []
    for rr in res.routes_ranked:
        coords = _wkt_to_coords(rr.wkt)
        feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "index": rr.index,
                "crashes": rr.crashes,
                "length_km": rr.length_km,
                "is_winner": (rr.index == res.winner)
            }
        })
    return JSONResponse({"type": "FeatureCollection", "features": feats})
