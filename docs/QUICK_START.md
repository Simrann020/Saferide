# SafeRide - Quick Start Guide

This guide will help you run the SafeRide project locally on your machine.

## Prerequisites

Before starting, make sure you have:
- ✅ **Docker** and **Docker Compose** installed
- ✅ **Python 3.11+** installed
- ✅ **pip** (Python package manager)

## Step-by-Step Instructions

### Step 1: Start the Database

The database runs in Docker using PostgreSQL with PostGIS extension.

```bash
# Navigate to project root
cd "/Users/simran/Documents/CUB Assignments/Project DCSC/Saferide Final"

# Start the database container
docker-compose up -d
```

This will:
- Start a PostgreSQL 16 database with PostGIS extension
- Initialize the schema automatically from `safer-ride/db/init/` scripts
- Expose PostgreSQL on port `5432`

**Verify it's running:**
```bash
docker ps
# You should see a container named "safer_ride_db"
```

**Check database logs (if needed):**
```bash
docker logs safer_ride_db
```

### Step 2: Load Data (Optional - if you have data files)

If you have crash data, 311 reports, or bikeway data to load:

```bash
# Install ETL dependencies
cd etl
pip install -r requirements.txt

# Load crash data
python load_crash.py

# Load 311 hazard data
python load_311.py

# Load bikeway data
python load_bikeway.py
```

**Note:** The ETL scripts expect data files in the `data/` directory. Check each script to see what files it expects.

### Step 3: Start the API

You can run the API in two ways:

#### Option A: Run Locally (Recommended for Development)

```bash
# Navigate to API directory
cd saferide-api

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or create a .env file)
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=safer_ride
export PGUSER=postgres
export PGPASSWORD=postgres

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

The `--reload` flag enables auto-reload during development.

#### Option B: Run with Docker

```bash
cd saferide-api

# Build the image
docker build -t saferide-api .

# Run the container
docker run -d \
  -p 8080:8080 \
  -e PGHOST=host.docker.internal \
  -e PGPORT=5432 \
  -e PGDATABASE=safer_ride \
  -e PGUSER=postgres \
  -e PGPASSWORD=postgres \
  saferide-api
```

**Verify API is running:**
```bash
# Test health endpoint
curl http://localhost:8080/health

# Or open in browser
open http://localhost:8080/docs
```

The API will be available at:
- **Health check**: `http://localhost:8080/health`
- **API docs**: `http://localhost:8080/docs`
- **Route ranking**: `POST http://localhost:8080/routes/rank`

### Step 4: Serve the Frontend UI

The UI is a static HTML file. You can serve it with any HTTP server:

#### Option A: Python HTTP Server (Easiest)

```bash
# Navigate to UI directory
cd safe-ride-ui

# Start a simple HTTP server
python3 -m http.server 8000
```

#### Option B: Node.js http-server

```bash
cd safe-ride-ui
npx http-server -p 8000
```

#### Option C: Open Directly

You can also open `safe-ride-ui/index.html` directly in a browser, but some features may not work due to CORS restrictions.

**Access the UI:**
Open your browser and go to: `http://localhost:8000`

**Note:** The UI expects the API at `http://127.0.0.1:8080`. If your API runs on a different host/port, update the `API_BASE` variable in `safe-ride-ui/index.html` or `app.js`.

## Complete Startup Script

Here's a quick script to start everything at once:

```bash
#!/bin/bash
# Start all services

# 1. Start database
echo "Starting database..."
docker-compose up -d

# 2. Wait for database to be ready
echo "Waiting for database..."
sleep 5

# 3. Start API (in background)
echo "Starting API..."
cd saferide-api
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=safer_ride
export PGUSER=postgres
export PGPASSWORD=postgres
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload &
API_PID=$!

# 4. Start UI (in background)
echo "Starting UI..."
cd ../safe-ride-ui
python3 -m http.server 8000 &
UI_PID=$!

echo ""
echo "✅ Services started!"
echo "   - Database: localhost:5432"
echo "   - API: http://localhost:8080"
echo "   - UI: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all services"
echo "API PID: $API_PID"
echo "UI PID: $UI_PID"

# Wait for interrupt
wait
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if container is running
docker ps

# Check database logs
docker logs safer_ride_db

# Test database connection
psql -h localhost -U postgres -d safer_ride
# Password: postgres
```

### API Not Starting

```bash
# Check Python version (needs 3.11+)
python3 --version

# Verify dependencies
pip list | grep -E "fastapi|uvicorn|sqlalchemy"

# Check environment variables
echo $PGHOST
echo $PGDATABASE
```

### UI Not Connecting to API

```bash
# Test API endpoint
curl http://localhost:8080/health

# Check browser console for errors (F12 in browser)
# Update API_BASE in index.html if needed
```

### Port Already in Use

If port 5432, 8080, or 8000 is already in use:

```bash
# Find what's using the port
lsof -i :8080
lsof -i :8000
lsof -i :5432

# Stop the conflicting service or change ports
```

## Stopping Services

```bash
# Stop database
docker-compose down

# Stop API (if running in terminal, press Ctrl+C)
# Or find and kill the process:
pkill -f "uvicorn app.main:app"

# Stop UI server
pkill -f "http.server"
```

## Next Steps

- **Load your data**: Use the ETL scripts to load crash, 311, and bikeway data
- **Test the API**: Visit `http://localhost:8080/docs` for interactive API documentation
- **Use the UI**: Open `http://localhost:8000` and try ranking some routes
- **Check logs**: Monitor API logs in the terminal and database logs with `docker logs safer_ride_db`

## Configuration

### Environment Variables

The API uses these environment variables (with defaults):
- `PGHOST` (default: `localhost`)
- `PGPORT` (default: `5432`)
- `PGDATABASE` (default: `safer_ride`)
- `PGUSER` (default: `postgres`)
- `PGPASSWORD` (default: `postgres`)

### OSRM Routing (Optional)

If you want to use a custom OSRM server:
- `OSRM_URL` - Generic OSRM server URL
- `OSRM_URL_DRIVING` - Driving-specific OSRM URL
- `OSRM_URL_CYCLING` - Cycling-specific OSRM URL
- `OSRM_URL_WALKING` - Walking-specific OSRM URL

## Project Structure

```
Saferide Final/
├── docker-compose.yml          # Database service
├── safer-ride/db/init/         # Database initialization scripts
├── saferide-api/               # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   ├── db.py              # Database connection
│   │   └── routes_rank.py     # Route ranking endpoints
│   └── requirements.txt
├── safe-ride-ui/              # Frontend
│   ├── index.html
│   └── app.js
├── etl/                       # Data loading scripts
│   ├── load_crash.py
│   ├── load_311.py
│   └── load_bikeway.py
└── data/                      # Data files
```

## Need Help?

- Check the main `README.md` for more details
- Review `PROJECT_DOCUMENTATION.md` for architecture details
- Check API documentation at `http://localhost:8080/docs` when running

