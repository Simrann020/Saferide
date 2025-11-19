#!/bin/bash
set -e

echo "🚀 SafeRide API Container Starting..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
for i in {1..15}; do
    if python3 -c "import psycopg2; psycopg2.connect('postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE')" 2>/dev/null; then
        echo "✅ Database ready!"
        break
    fi
    sleep 1
done

echo "🚀 Starting SafeRide API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
