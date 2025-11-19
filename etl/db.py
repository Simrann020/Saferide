# etl/db.py
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
ENGINE_URL = os.getenv("DATABASE_URL")
assert ENGINE_URL, "DATABASE_URL not found. Check your .env."

engine = create_engine(ENGINE_URL, future=True)

if __name__ == "__main__":
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT postgis_version();")).scalar_one()
        tables = conn.execute(text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema = 'saferide'
            ORDER BY table_name;
        """)).fetchall()
        print("PostGIS:", ver)
        print("Tables:", tables)
