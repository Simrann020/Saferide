# etl/load_bikeway.py
import os, sys, math
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# --- Config ---
# Your WKT looks like Colorado State Plane Central (ftUS) ~ EPSG:2232.
# If your data is actually WGS84 already, change SRC_SRID to 4326.
SRC_SRID = 2232  # source SRID for WKT -> we will ST_Transform(..., 4326)

# -------------

def pick(cols, *names):
    for n in names:
        if n in cols: return n
    return None

def to_float(x):
    try:
        # accept "491.0" / "491" / "491,0" / blanks
        s = str(x).strip().replace(",", "")
        return float(s) if s not in ("", "nan", "None") else math.nan
    except Exception:
        return math.nan

def main():
    load_dotenv()
    ENGINE_URL = os.getenv("DATABASE_URL")
    assert ENGINE_URL, "DATABASE_URL missing. Put it in .env (see earlier steps)."
    engine = create_engine(ENGINE_URL, future=True)

    src = sys.argv[1] if len(sys.argv) > 1 else "data/bicycle_inventory.csv"
    df = pd.read_csv(src, dtype=str).fillna("")

    # Likely headers (from your sample)
    c_id     = pick(df.columns, "FID", "fid", "OBJECTID", "objectid", "geomid")
    c_name   = pick(df.columns, "name", "NAME", "alt_name")
    c_type   = pick(df.columns, "fac_type", "FAC_TYPE")
    c_status = pick(df.columns, "status", "STATUS")
    c_lenft  = pick(df.columns, "len_ft", "LEN_FT", "length_ft", "shape_stle")  # len_ft preferred
    c_wkt    = pick(df.columns, "geom", "GEOM", "WKT", "wkt")

    if c_id is None or c_wkt is None:
        raise SystemExit(
            f"CSV must contain an ID column and a WKT column. "
            f"Got columns: {list(df.columns)}"
        )

    # Build rows
    rows = []
    for _, r in df.iterrows():
        wkt = r[c_wkt].strip()
        if not wkt or "LINESTRING" not in wkt.upper():
            continue
        rows.append({
            "src_id": str(r[c_id]),
            "class": (r[c_type] or "").strip().lower() if c_type else "",
            "on_off": "",  # CSV may not have this, set to empty or derive from facility_type
            "status": (r[c_status] or "").strip().upper() if c_status else "",
            "wkt": wkt,
        })

    if not rows:
        print("No valid LINESTRING features found in the file.")
        return

    with engine.begin() as conn:
        # Figure out which PK the table uses: infra_id, way_id, or id
        info = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'saferide' AND table_name = 'bikeway';
        """)).fetchall()
        cols = {c[0] for c in info}
        if "infra_id" in cols:
            pk_col = "infra_id"
        elif "way_id" in cols:
            pk_col = "way_id"
        elif "id" in cols:
            pk_col = "id"
        else:
            raise SystemExit(
                "Could not find 'infra_id', 'way_id', or 'id' column in saferide.bikeway. "
                "Run \\d saferide.bikeway to inspect the table."
            )

        # Build SQL dynamically to match the PK name
        sql = text(f"""
        INSERT INTO saferide.bikeway ({pk_col}, class, on_off, status, geom)
        VALUES (:src_id, :class, :on_off, :status,
                ST_Transform(ST_GeomFromText(:wkt, {SRC_SRID}), 4326))
        ON CONFLICT ({pk_col}) DO UPDATE SET
          class  = EXCLUDED.class,
          on_off = EXCLUDED.on_off,
          status = EXCLUDED.status,
          geom   = EXCLUDED.geom;
        """)

        conn.execute(sql, rows)

    print(f"Loaded {len(rows)} bikeway segments from {src} (PK column used: {pk_col}, SRID in: {SRC_SRID} → 4326)")

if __name__ == "__main__":
    main()
