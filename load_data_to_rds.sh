#!/bin/bash
# Load crash, hazard, and bikeway data to RDS

set -e

cd "$(dirname "$0")"

echo "📊 Loading data to RDS..."

# Get database password
DB_PASSWORD=$(cat /tmp/saferide_db_password.txt)
export DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@saferide-db.cdiqwk6682ia.us-west-2.rds.amazonaws.com:5432/safer_ride"

echo "✅ Database connection configured"
echo ""

# Load crash data
echo "🚗 Loading crash data..."
python3 etl/load_crash.py data/crash.csv

echo ""

# Load 311 hazard data
echo "⚠️  Loading 311 hazard data..."
python3 etl/load_311.py data/crash_311.csv

echo ""

# Load bikeway data
echo "🚴 Loading bikeway data..."
python3 etl/load_bikeway.py data/bicycle_inventory.csv

echo ""
echo "✅ All data loaded!"
echo ""
echo "Verifying data counts..."
python3 <<EOF
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    crash_count = conn.execute(text("SELECT COUNT(*) FROM saferide.crash")).scalar()
    hazard_count = conn.execute(text("SELECT COUNT(*) FROM saferide.hazard")).scalar()
    bikeway_count = conn.execute(text("SELECT COUNT(*) FROM saferide.bikeway")).scalar()
    print(f"📊 Crashes: {crash_count:,}")
    print(f"⚠️  Hazards: {hazard_count:,}")
    print(f"🚴 Bikeways: {bikeway_count:,}")
EOF

