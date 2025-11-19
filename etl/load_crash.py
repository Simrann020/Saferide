# etl/load_crash.py
import sys, os, math
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
ENGINE_URL = os.getenv("DATABASE_URL")
assert ENGINE_URL, "DATABASE_URL not found. Create a .env with DATABASE_URL=..."

engine = create_engine(ENGINE_URL, future=True)
SRC = sys.argv[1] if len(sys.argv) > 1 else "data/crash.csv"

# ---------- 1) READ ----------
df = pd.read_csv(SRC, dtype=str).fillna("")

def pick(cols, *names):
    for n in names:
        if n in cols: return n
    return None

col_id   = pick(df.columns, "incident_id", "object_id", "INCIDENT_ID", "objectid", "OBJECTID")
col_lon  = pick(df.columns, "geo_lon", "POINT_X", "Longitude", "lon", "LONGITUDE")
col_lat  = pick(df.columns, "geo_lat", "POINT_Y", "Latitude", "lat", "LATITUDE")
col_time = pick(df.columns, "first_occurrence_date", "occurred_at", "FIRST_OCCURRENCE_DATE", "first_occurrence_dttm")
col_fat  = pick(df.columns, "FATALITIES", "fatalities", "Fatalities")
col_ser  = pick(df.columns, "SERIOUSLY_INJURED", "seriously_injured", "Seriously_Injured")

need = [col_id, col_lon, col_lat, col_time]
missing = [nm for nm, c in zip(["id","lon","lat","time"], need) if c is None]
if missing:
    raise SystemExit(f"Missing required columns in {SRC}: {missing}. Found: {list(df.columns)}")

# ---------- 2) CLEAN ----------
def to_float(x):
    try: return float(x)
    except: return math.nan

def to_int(x):
    try: return int(float(x))
    except: return 0

df["_lon"] = df[col_lon].map(to_float)
df["_lat"] = df[col_lat].map(to_float)
df = df[pd.notnull(df["_lon"]) & pd.notnull(df["_lat"])]

# Parse times as tz-aware UTC
t_aware = pd.to_datetime(df[col_time], errors="coerce", utc=True)
valid = pd.notnull(t_aware)
df = df[valid].copy()
t_aware = t_aware[valid]

# ---- FILTER using a tz-aware cutoff, then drop tz ----
cut_aware = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=5)
mask = t_aware >= cut_aware
df = df[mask].copy()
t_aware = t_aware[mask]

# Now make naive UTC for DB
df["_occurred_at"] = t_aware.dt.tz_convert("UTC").dt.tz_localize(None)

# Severity: 1=fatal, 2=serious, 3=minor
fat = df[col_fat].map(to_int) if col_fat else pd.Series([0]*len(df), index=df.index)
ser = df[col_ser].map(to_int) if col_ser else pd.Series([0]*len(df), index=df.index)
df["_severity"] = 3
df.loc[ser > 0, "_severity"] = 2
df.loc[fat > 0, "_severity"] = 1

# De-dup
df = df.drop_duplicates(subset=[col_id])

# ---------- 3) UPSERT ----------
rows = [{
    "crash_id": str(r[col_id]),
    "occurred_at": r["_occurred_at"].to_pydatetime(),
    "severity": int(r["_severity"]),
    "lon": float(r["_lon"]),
    "lat": float(r["_lat"]),
} for _, r in df.iterrows()]

sql = text("""
INSERT INTO saferide.crash (crash_id, occurred_at, severity, geom)
VALUES (:crash_id, :occurred_at, :severity, ST_SetSRID(ST_Point(:lon,:lat),4326))
ON CONFLICT (crash_id) DO UPDATE SET
  occurred_at = EXCLUDED.occurred_at,
  severity    = EXCLUDED.severity,
  geom        = EXCLUDED.geom;
""")

with engine.begin() as conn:
    if rows:
        conn.execute(sql, rows)

print(f"Loaded {len(rows)} crashes from {SRC}")
