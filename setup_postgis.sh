#!/bin/bash
# Enable PostGIS extension on RDS instance

set -e

DB_INSTANCE_ID="saferide-db"
REGION="us-west-2"

echo "🔍 Getting RDS endpoint..."
ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_ID \
    --region $REGION \
    --query "DBInstances[0].Endpoint.Address" \
    --output text 2>/dev/null)

if [ -z "$ENDPOINT" ] || [ "$ENDPOINT" == "None" ]; then
    echo "❌ Could not get RDS endpoint. Is the instance available?"
    echo "Run: ./check_rds_status.sh"
    exit 1
fi

echo "Endpoint: $ENDPOINT"
echo ""

# Get password
if [ -f "/tmp/saferide_db_password.txt" ]; then
    DB_PASSWORD=$(cat /tmp/saferide_db_password.txt)
else
    echo "⚠️  Password file not found. Enter password manually:"
    read -s DB_PASSWORD
fi

echo "📦 Enabling PostGIS extension..."
echo ""

# Enable PostGIS
PGPASSWORD="$DB_PASSWORD" psql -h "$ENDPOINT" -U postgres -d safer_ride <<EOF
-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Verify installation
SELECT PostGIS_version();
\q
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PostGIS enabled successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Run database initialization scripts:"
    echo "      psql -h $ENDPOINT -U postgres -d safer_ride -f safer-ride/db/init/00_extensions.sql"
    echo "      psql -h $ENDPOINT -U postgres -d safer_ride -f safer-ride/db/init/10_schema.sql"
    echo "      # ... continue with other init scripts"
    echo ""
    echo "   2. Load data using ETL scripts:"
    echo "      export PGHOST=$ENDPOINT"
    echo "      python etl/load_crash.py"
    echo "      python etl/load_311.py"
    echo "      python etl/load_bikeway.py"
else
    echo ""
    echo "❌ Failed to enable PostGIS. Check your connection and credentials."
    exit 1
fi

