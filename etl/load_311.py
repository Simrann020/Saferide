# etl/load_311.py
import sys, os, re, math
import pandas as pd
from sqlalchemy import text, create_engine
from dotenv import load_dotenv

load_dotenv()
ENGINE_URL = os.getenv("DATABASE_URL")
engine = create_engine(ENGINE_URL, future=True)

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/crash_311.csv"  # your file name

# ---- 1) Read CSV ----
df = pd.read_csv(SRC, dtype=str).fillna("")

# Column helpers (accept a few possible spellings)
def pick(*names):
    for n in names:
        if n in df.columns:
            return n
    return None

col_id   = pick("OBJECTID", "ObjectId", "Id", "OBJECT ID")
col_lon  = pick("Longitude", "lon", "LONGITUDE", "POINT_X", "geo_lon")
col_lat  = pick("Latitude", "lat", "LATITUDE", "POINT_Y", "geo_lat")
col_cts  = pick("Case Status", "Status")
col_ctd  = pick("Case Created dttm", "Case Created Date", "Created Date", "Opened")
col_type = pick("Type")
col_topic= pick("Topic")
col_sum  = pick("Case Summary", "Summary")

req = [col_id, col_lon, col_lat, col_cts, col_ctd]
missing = [n for n in ["id","lon","lat","status","created_at"] if req[["id","lon","lat","status","created_at"].index(n)] is None]
if any(missing):
    raise SystemExit(f"Missing required columns in {SRC}: {missing}")

# ---- 2) Basic cleaning ----
def to_float(s):
    try:
        return float(s)
    except:
        return math.nan

df["_lon"] = df[col_lon].apply(to_float)
df["_lat"] = df[col_lat].apply(to_float)
df = df[pd.notnull(df["_lon"]) & pd.notnull(df["_lat"])]

# timestamps
df["_opened_at"] = pd.to_datetime(df[col_ctd], errors="coerce", utc=False)

# status normalize
def norm_status(s):
    s = s.strip().lower()
    if not s: return "unknown"
    if s.startswith("closed"): return "closed"
    if "progress" in s: return "in_progress"
    if s.startswith("open"): return "open"
    return s.replace(" ", "_")

df["_status"] = df[col_cts].apply(norm_status)

# category from topic/type/summary keywords
def norm_category(row):
    src = " ".join([row.get(col_topic,""), row.get(col_type,""), row.get(col_sum,"")]).lower()
    if any(k in src for k in ["pothole", "potholes"]): return "pothole"
    if any(k in src for k in ["debris", "glass", "trash", "sand", "gravel"]): return "debris"
    if any(k in src for k in ["signal", "traffic light", "stop light"]): return "signal"
    if any(k in src for k in ["bike", "bicycle", "lane block", "bike lane", "path blocked"]): return "bike_blocked"
    if any(k in src for k in ["snow", "ice"]): return "snow_ice"
    return "other"

df["_category"] = df.apply(norm_category, axis=1)

# keep last 12 months (optional; comment out to load all)
cut = pd.Timestamp.utcnow() - pd.Timedelta(days=365)
df = df[df["_opened_at"] >= cut.tz_localize(None)] if df["_opened_at"].notna().any() else df

# Deduplicate on id
df = df.drop_duplicates(subset=[col_id])

# ---- 3) Insert into PostGIS ----
rows = []
for _, r in df.iterrows():
    rows.append({
        "hazard_id": str(r[col_id]),
        "category": r["_category"],
        "status": r["_status"],
        "opened_at": None if pd.isna(r["_opened_at"]) else r["_opened_at"].to_pydatetime(),
        "closed_at": None,   # can be added if you have a close-date col
        "lon": float(r["_lon"]),
        "lat": float(r["_lat"]),
    })

sql = text("""
INSERT INTO saferide.hazard (hazard_id, category, status, opened_at, closed_at, geom)
VALUES (:hazard_id, :category, :status, :opened_at, :closed_at,
        ST_SetSRID(ST_Point(:lon, :lat), 4326))
ON CONFLICT (hazard_id) DO UPDATE SET
  category = EXCLUDED.category,
  status   = EXCLUDED.status,
  opened_at= COALESCE(EXCLUDED.opened_at, saferide.hazard.opened_at),
  closed_at= COALESCE(EXCLUDED.closed_at, saferide.hazard.closed_at),
  geom     = EXCLUDED.geom;
""")

with engine.begin() as conn:
    conn.execute(sql, rows)

print(f"Loaded {len(rows)} hazards from {SRC}")
