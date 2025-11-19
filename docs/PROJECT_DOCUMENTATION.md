# SafeRide - Risk-Aware Bicycle Routing
## AWS Cloud Deployment Documentation

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [AWS Services Used](#aws-services-used)
3. [Architecture Diagram](#architecture-diagram)
4. [Data Flow](#data-flow)
5. [Component Details](#component-details)
6. [Deployment Summary](#deployment-summary)
7. [Access URLs](#access-urls)
8. [Cost Considerations](#cost-considerations)

---

## 🎯 Project Overview

**SafeRide** is a risk-aware bicycle routing application that helps cyclists find the safest routes by analyzing historical crash data, 311 hazard reports, and bikeway infrastructure. The application provides route alternatives ranked by safety metrics, helping cyclists make informed decisions.

### Key Features
- **Route Ranking**: Multiple route alternatives ranked by crash count and distance
- **Risk Visualization**: Interactive map showing crash hotspots and route safety
- **Real-time API**: Serverless API for route scoring and ranking
- **Spatial Analysis**: PostGIS-powered geographic queries for route risk assessment

---

## ☁️ AWS Services Used

### 1. **Amazon RDS (Relational Database Service)**
- **Service**: PostgreSQL 16.10 with PostGIS extension
- **Purpose**: Primary data store for crash data, hazards, and bikeway infrastructure
- **Configuration**:
  - Instance: `db.t3.micro` (Free Tier eligible)
  - Region: `us-west-2` (Oregon)
  - Database: `safer_ride`
  - Endpoint: `saferide-db.cdiqwk6682ia.us-west-2.rds.amazonaws.com`
- **Features**:
  - PostGIS 3.4 for spatial queries
  - Automated backups (1 day retention)
  - VPC isolation for security
  - Multi-AZ disabled (single AZ for cost savings)

### 2. **AWS Lambda**
- **Service**: Serverless compute
- **Purpose**: Hosts the FastAPI backend application
- **Configuration**:
  - Runtime: Python 3.11
  - Function: `saferide-api`
  - Handler: `lambda_handler.handler`
  - Memory: 512 MB
  - Timeout: 30 seconds
- **Technology Stack**:
  - FastAPI web framework
  - Mangum adapter (ASGI to Lambda)
  - SQLAlchemy for database connections
  - psycopg3 for PostgreSQL

### 3. **Amazon API Gateway**
- **Service**: REST API
- **Purpose**: HTTPS endpoint for the Lambda function
- **Configuration**:
  - Type: REST API
  - Stage: `prod`
  - Region: `us-west-2`
  - API ID: `39lch19vrb`
- **Endpoints**:
  - `GET /health` - Health check
  - `POST /routes/rank` - Route ranking endpoint
- **Features**:
  - CORS enabled for frontend access
  - Lambda proxy integration
  - Automatic HTTPS/SSL

### 4. **Amazon S3 (Simple Storage Service)**
- **Purpose**: Hosts static frontend and stores data files
- **Buckets Created**:
  1. **`saferide-ui-505877`**
     - Purpose: Static website hosting for frontend
     - Configuration: Public read access, website hosting enabled
     - Files: `index.html`, `app.js`, `styles.css`
   
  2. **`saferide-crash-data-505877`**
     - Purpose: Data lake for crash CSV files
     - Files: `crash.csv` (141 MB, 274K rows)
   
  3. **`saferide-311-data-505877`**
     - Purpose: Data lake for 311 hazard reports
     - Files: `crash_311.csv` (87 MB)
   
  4. **`saferide-bikeway-data-505877`**
     - Purpose: Data lake for bikeway inventory
     - Files: `bicycle_inventory.csv` (26 MB)
   
  5. **`saferide-tiles-505877`**
     - Purpose: Pre-generated risk tiles for map visualization
     - Files: GeoJSON tile files

### 5. **Amazon VPC (Virtual Private Cloud)**
- **Purpose**: Network isolation for RDS database
- **Configuration**:
  - Default VPC used
  - Subnet group: `saferide-db-subnet-group`
  - Availability Zones: `us-west-2a`, `us-west-2b`, `us-west-2c`

### 6. **Security Groups**
- **RDS Security Group**: `saferide-db-sg`
  - Allows inbound PostgreSQL (5432) from Lambda security group
  - Outbound: All traffic

### 7. **IAM (Identity and Access Management)**
- **Lambda Execution Role**: `saferide-lambda-role`
  - Permissions:
    - RDS read/write access
    - CloudWatch Logs
    - VPC access (for RDS connection)

### 8. **CloudWatch Logs**
- **Purpose**: Automatic logging for Lambda function
- **Log Group**: `/aws/lambda/saferide-api`
- **Retention**: Default (never expire)

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                    (Mapbox GL JS Frontend)                       │
└────────────────────────────┬──────────────────────────────────┘
                              │ HTTPS
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                    Amazon S3                                    │
│              saferide-ui-505877                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Static Website Hosting                                 │   │
│  │  - index.html                                           │   │
│  │  - app.js (Frontend Logic)                              │   │
│  │  - styles.css                                           │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ API Calls (CORS)
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                  Amazon API Gateway                              │
│              REST API (prod stage)                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  POST /routes/rank                                      │   │
│  │  GET  /health                                           │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              │ Lambda Invocation
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                    AWS Lambda                                    │
│              saferide-api (Python 3.11)                         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  FastAPI Application                                    │   │
│  │  - Route ranking logic                                  │   │
│  │  - Crash data scoring                                   │   │
│  │  - PostGIS spatial queries                              │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              │ PostgreSQL Connection
                              │ (via VPC)
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                    Amazon RDS                                   │
│         PostgreSQL 16.10 + PostGIS 3.4                         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Database: safer_ride                                    │   │
│  │  Schema: saferide                                       │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │ Tables:                                          │  │   │
│  │  │  - crash (71,000+ records)                        │  │   │
│  │  │  - hazard (311 reports)                           │  │   │
│  │  │  - bikeway (infrastructure)                       │  │   │
│  │  │  - crash_weights (view)                          │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │ PostGIS Functions:                                │  │   │
│  │  │  - ST_GeomFromText()                              │  │   │
│  │  │  - ST_Buffer()                                    │  │   │
│  │  │  - ST_Intersects()                                │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Amazon S3 (Data Lake)                         │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │ Crash Data   │ 311 Data    │ Bikeway Data │ Risk Tiles   │ │
│  │ Bucket       │ Bucket      │ Bucket       │ Bucket       │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### 1. **Initial Data Loading (ETL Process)**
```
CSV Files (Local/S3) 
    ↓
ETL Scripts (Python)
    ↓
Data Transformation & Cleaning
    ↓
PostgreSQL INSERT (RDS)
    ↓
PostGIS Spatial Indexing
```

**ETL Scripts**:
- `etl/load_crash.py` - Loads crash data (71,000+ records)
- `etl/load_311.py` - Loads 311 hazard reports
- `etl/load_bikeway.py` - Loads bikeway infrastructure

**Data Processing**:
- Filters crashes from last 5 years
- Converts coordinates to PostGIS geometry
- Assigns severity levels (1=fatal, 2=serious, 3=minor)
- Creates spatial indexes for fast queries

### 2. **User Request Flow**
```
1. User opens frontend (S3 website)
   ↓
2. User enters start/end locations
   ↓
3. Frontend calls Mapbox API for route alternatives
   ↓
4. Frontend sends routes to API Gateway
   POST /routes/rank
   {
     "start": [-105.0, 39.7],
     "end": [-104.99, 39.75],
     "mode": "driving",
     "buffer_m": 60,
     "max_alternatives": 3
   }
   ↓
5. API Gateway invokes Lambda function
   ↓
6. Lambda processes request:
   a. Receives route geometries (WKT format)
   b. For each route:
      - Creates buffer around route (60m default)
      - Queries crash data within buffer using PostGIS
      - Counts crashes by severity
      - Calculates risk score
   c. Ranks routes by crash count and distance
   ↓
7. Lambda returns ranked routes
   {
     "winner": 2,
     "routes_ranked": [
       {
         "index": 0,
         "length_km": 8.232,
         "crashes": 998,
         "wkt": "LINESTRING(...)"
       },
       ...
     ]
   }
   ↓
8. Frontend receives response
   ↓
9. Frontend visualizes routes on map:
   - Winner route highlighted (green)
   - Alternative routes shown (yellow/red by risk)
   - Crash counts displayed
   - Route cards with statistics
```

### 3. **Database Query Flow (Inside Lambda)**
```sql
-- Example query executed for each route
SELECT COUNT(*) as crash_count
FROM saferide.crash_weights c
WHERE ST_Intersects(
    c.geom,
    ST_Buffer(
        ST_GeomFromText('LINESTRING(...)', 4326),
        0.0006  -- ~60 meters in degrees
    )
)
```

**PostGIS Functions Used**:
- `ST_GeomFromText()` - Converts WKT to geometry
- `ST_Buffer()` - Creates buffer around route
- `ST_Intersects()` - Finds crashes within buffer
- `ST_SetSRID()` - Sets coordinate system (4326 = WGS84)

---

## 🔧 Component Details

### Frontend (S3 Static Website)
- **Technology**: Vanilla JavaScript, Mapbox GL JS
- **Location**: `saferide-ui-505877` S3 bucket
- **Features**:
  - Interactive map with route visualization
  - Route ranking display
  - Crash count visualization
  - Responsive UI

### Backend (Lambda + FastAPI)
- **Technology**: Python 3.11, FastAPI, Mangum
- **Location**: AWS Lambda function `saferide-api`
- **Key Endpoints**:
  - `GET /health` - Health check
  - `POST /routes/rank` - Route ranking with crash analysis
- **Dependencies**:
  - `fastapi` - Web framework
  - `mangum` - ASGI to Lambda adapter
  - `sqlalchemy` - Database ORM
  - `psycopg` - PostgreSQL driver
  - `pydantic` - Data validation

### Database (RDS PostgreSQL)
- **Schema**: `saferide`
- **Tables**:
  - `crash` - Crash incidents (71,000+ records)
  - `hazard` - 311 hazard reports
  - `bikeway` - Bikeway infrastructure
  - `crash_weights` - Materialized view for scoring
- **Indexes**:
  - Spatial indexes (GIST) on geometry columns
  - Time-based indexes for filtering

---

## 📊 Deployment Summary

### Infrastructure Created

| Service | Resource Name | Status |
|---------|--------------|--------|
| RDS | `saferide-db` | ✅ Available |
| Lambda | `saferide-api` | ✅ Deployed |
| API Gateway | `39lch19vrb` | ✅ Deployed |
| S3 | `saferide-ui-505877` | ✅ Public |
| S3 | `saferide-crash-data-505877` | ✅ Created |
| S3 | `saferide-311-data-505877` | ✅ Created |
| S3 | `saferide-bikeway-data-505877` | ✅ Created |
| S3 | `saferide-tiles-505877` | ✅ Created |
| IAM Role | `saferide-lambda-role` | ✅ Created |
| Security Group | `saferide-db-sg` | ✅ Active |
| Subnet Group | `saferide-db-subnet-group` | ✅ Active |

### Data Loaded

| Table | Records | Status |
|-------|---------|--------|
| `saferide.crash` | 71,000+ | ✅ Loaded |
| `saferide.hazard` | 0 | ⏳ Optional |
| `saferide.bikeway` | 0 | ⏳ Optional |

### Configuration

- **Region**: `us-west-2` (Oregon)
- **Database**: PostgreSQL 16.10 with PostGIS 3.4
- **Lambda Runtime**: Python 3.11
- **API Stage**: `prod`
- **CORS**: Enabled for S3 website

---

## 🌐 Access URLs

### Frontend
- **URL**: http://saferide-ui-505877.s3-website-us-west-2.amazonaws.com
- **Type**: Static website hosting
- **Status**: ✅ Publicly accessible

### API Endpoints
- **Base URL**: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod
- **Health Check**: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/health
- **Route Ranking**: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/routes/rank
- **Status**: ✅ Operational

### Database
- **Endpoint**: `saferide-db.cdiqwk6682ia.us-west-2.rds.amazonaws.com:5432`
- **Database**: `safer_ride`
- **Access**: Via Lambda (VPC) or direct connection with credentials
- **Status**: ✅ Available

---

## 💰 Cost Considerations

### Free Tier Eligible
- **RDS**: `db.t3.micro` instance (750 hours/month for 12 months)
- **Lambda**: 1M requests/month, 400,000 GB-seconds
- **API Gateway**: 1M API calls/month
- **S3**: 5 GB storage, 20,000 GET requests
- **Data Transfer**: 100 GB out to internet

### Estimated Monthly Cost (After Free Tier)
- **RDS**: ~$15/month (db.t3.micro)
- **Lambda**: ~$0.20/month (assuming 10K requests)
- **API Gateway**: ~$3.50/month (assuming 1M requests)
- **S3**: ~$0.50/month (assuming 5 GB storage)
- **Data Transfer**: ~$9/month (assuming 100 GB)
- **Total**: ~$28/month

### Cost Optimization Tips
1. Use RDS Reserved Instances for long-term savings
2. Enable S3 lifecycle policies for old data
3. Use CloudFront for S3 website (reduces data transfer costs)
4. Monitor Lambda cold starts and optimize memory
5. Use RDS snapshots for backups (cheaper than continuous backups)

---

## 🔐 Security Features

1. **VPC Isolation**: RDS database in private subnet
2. **Security Groups**: Restrictive firewall rules
3. **IAM Roles**: Least privilege access for Lambda
4. **HTTPS Only**: API Gateway enforces SSL/TLS
5. **CORS**: Configured for specific origins
6. **Database Credentials**: Stored securely, not in code

---

## 📈 Scalability

### Current Configuration
- **Lambda**: Auto-scales based on requests
- **RDS**: Single instance (can scale vertically)
- **API Gateway**: Handles millions of requests
- **S3**: Unlimited storage and bandwidth

### Future Scaling Options
1. **RDS Read Replicas**: For read-heavy workloads
2. **Lambda Provisioned Concurrency**: Reduce cold starts
3. **CloudFront**: CDN for frontend assets
4. **RDS Multi-AZ**: High availability
5. **ElastiCache**: Cache frequent queries

---

## 🚀 Next Steps / Future Enhancements

1. **Load Remaining Data**:
   - 311 hazard reports
   - Bikeway infrastructure data

2. **Performance Optimization**:
   - Add CloudFront for frontend
   - Implement caching layer
   - Optimize PostGIS queries

3. **Features**:
   - Real-time traffic integration
   - Weather-based risk factors
   - User route history
   - Mobile app

4. **Monitoring**:
   - CloudWatch dashboards
   - API Gateway metrics
   - RDS performance insights
   - Lambda error tracking

---

## 📝 Technical Stack Summary

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5, CSS3, JavaScript, Mapbox GL JS |
| **Backend** | Python 3.11, FastAPI, Mangum |
| **Database** | PostgreSQL 16.10, PostGIS 3.4 |
| **Compute** | AWS Lambda (Serverless) |
| **API** | Amazon API Gateway (REST) |
| **Storage** | Amazon S3 (Static hosting + Data lake) |
| **Database Hosting** | Amazon RDS |
| **Networking** | Amazon VPC, Security Groups |
| **Security** | IAM Roles, VPC Isolation |

---

## ✅ Deployment Checklist

- [x] RDS PostgreSQL instance created
- [x] PostGIS extension enabled
- [x] Database schema initialized
- [x] Crash data loaded (71,000+ records)
- [x] Lambda function deployed
- [x] API Gateway configured
- [x] CORS enabled
- [x] S3 buckets created
- [x] Frontend uploaded to S3
- [x] Public access configured
- [x] IAM roles and policies created
- [x] Security groups configured
- [x] API tested and working
- [x] Frontend accessible

---

## 📞 Support & Documentation

- **AWS Documentation**: https://docs.aws.amazon.com/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **PostGIS Documentation**: https://postgis.net/documentation/
- **Mapbox GL JS**: https://docs.mapbox.com/mapbox-gl-js/

---

**Project Status**: ✅ **FULLY DEPLOYED AND OPERATIONAL**

**Last Updated**: November 16, 2025

**Deployment Region**: us-west-2 (Oregon)

---

