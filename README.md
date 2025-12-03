# SafeRide Project

A crash-aware multi-route ranking service that helps users find safer routes for driving, cycling, and walking.

# Project Group 1
# Team Mates
## Rohan Jain and Simran Jadhav

## Architecture

- **Database**: PostgreSQL with PostGIS extension (Docker)
- **API**: FastAPI backend (`saferide-api/`)
- **UI**: Single-page web application (`safe-ride-ui/`)
- **ETL**: Python scripts to load crash, bikeway, and 311 data

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (if running API locally)
- pip (Python package manager)

## Quick Start

### 1. Start the Database

The database runs in Docker using `docker-compose.yml`:

```bash
docker-compose up -d
```

This will:
- Start a PostGIS database container
- Initialize the schema from `safer-ride/db/init/` scripts
- Expose PostgreSQL on port `5432`

**Note**: The `docker-compose.yml` references `./init` for initialization scripts. You may need to create a symlink or copy the init scripts:

```bash
# Create symlink from safer-ride/db/init to ./init
ln -s safer-ride/db/init init
```

Or update `docker-compose.yml` to point to the correct path:
```yaml
volumes:
  - ./safer-ride/db/init:/docker-entrypoint-initdb.d
```

### 2. Load Data (ETL)

After the database is running, load your data using the ETL scripts:

```bash
# Make sure you're in the project root
cd /Users/simran/Documents/CUB\ Assignments/Project\ DCSC/saferide

# Load crash data
python etl/load_crash.py

# Load 311 hazard data
python etl/load_311.py

# Load bikeway data
python etl/load_bikeway.py
```

**Note**: Check the ETL scripts to see what data files they expect and their locations.

### 3. Start the API

#### Option A: Using Docker

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

**Note**: The Dockerfile expects a `.env` file. You may need to create one or pass environment variables.

#### Option B: Run Locally

```bash
cd saferide-api

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or create a .env file)
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=safer_ride
export PGUSER=postgres
export PGPASSWORD=postgres

# Run the API
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at `http://localhost:8080`

- Health check: `http://localhost:8080/health`
- API docs: `http://localhost:8080/docs`
- Route ranking: `POST http://localhost:8080/routes/rank`

### 4. Serve the UI

The UI is a static HTML file. You can serve it with any HTTP server:

#### Option A: Python HTTP Server

```bash
cd safe-ride-ui
python3 -m http.server 8000
```

#### Option B: Node.js http-server

```bash
cd safe-ride-ui
npx http-server -p 8000
```

#### Option C: Open Directly

You can also open `safe-ride-ui/index.html` directly in a browser, but note that some features may not work due to CORS restrictions.

The UI will be available at `http://localhost:8000`

**Note**: The UI expects the API at `http://127.0.0.1:8080` (see line 115 in `index.html`). Update this if your API runs on a different host/port.

## Configuration

### Database Connection

The API uses these environment variables (with defaults):
- `PGHOST` (default: `localhost`)
- `PGPORT` (default: `5432`)
- `PGDATABASE` (default: `safer_ride`)
- `PGUSER` (default: `postgres`)
- `PGPASSWORD` (default: `postgres`)

### OSRM Routing

The API can use OSRM for route calculation. Configure via:
- `OSRM_URL` - Generic OSRM server URL template
- `OSRM_URL_DRIVING` - Driving-specific OSRM URL
- `OSRM_URL_CYCLING` - Cycling-specific OSRM URL
- `OSRM_URL_WALKING` - Walking-specific OSRM URL

If not set, it defaults to the public OSRM demo server.

## API Endpoints

- `GET /health` - Health check
- `GET /version` - API version
- `POST /routes/rank` - Rank routes by safety
- `POST /routes/rank_fc` - Rank routes (returns GeoJSON FeatureCollection)

See `http://localhost:8080/docs` for interactive API documentation.

## Troubleshooting

### Database Connection Issues

- Ensure Docker container is running: `docker ps`
- Check database logs: `docker logs safer_ride_db`
- Verify connection: `psql -h localhost -U postgres -d safer_ride`

### API Not Starting

- Check Python version: `python3 --version` (needs 3.11+)
- Verify dependencies: `pip list`
- Check environment variables are set correctly

### UI Not Connecting to API

- Verify API is running: `curl http://localhost:8080/health`
- Check browser console for CORS errors
- Update `API_BASE` in `index.html` if API is on different host/port

## Project Structure

```
saferide/
├── docker-compose.yml          # Database service
├── safer-ride/db/init/         # Database initialization scripts
├── saferide-api/               # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   ├── db.py              # Database connection
│   │   └── routes_rank.py     # Route ranking endpoints
│   ├── Dockerfile
│   └── requirements.txt
├── safe-ride-ui/              # Frontend
│   └── index.html
├── etl/                       # Data loading scripts
│   ├── load_crash.py
│   ├── load_311.py
│   └── load_bikeway.py
└── data/                      # Data files
```

## Development

To run in development mode with auto-reload:

```bash
# API
cd saferide-api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```


