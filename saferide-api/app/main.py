# saferide-api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .db import init_database
from .routes_rank import router as rank_router

app = FastAPI(
    title="Saferide API",
    version="1.0.0",
    description="Crash-aware multi-route ranking service",
)

# CORS (safe defaults; tweak if you host elsewhere)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

# Initialize database on module load
init_database()

@app.get("/", response_class=HTMLResponse)
def root():
    """Root endpoint with interactive HTML dashboard"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SafeRide API - Crash-Aware Route Ranking</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
                background: linear-gradient(135deg, #0b69ff 0%, #0550d9 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 900px;
                width: 100%;
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #0b69ff 0%, #0550d9 100%);
                color: white;
                padding: 60px 40px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 48px;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 15px;
            }
            
            .header p {
                font-size: 18px;
                opacity: 0.9;
            }
            
            .content {
                padding: 40px;
            }
            
            .version {
                background: #f0f4ff;
                border-left: 4px solid #0b69ff;
                padding: 15px 20px;
                margin-bottom: 30px;
                border-radius: 8px;
                font-size: 14px;
                color: #1e293b;
            }
            
            .endpoints {
                margin-bottom: 30px;
            }
            
            .endpoints h2 {
                font-size: 24px;
                color: #1e293b;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .endpoint-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }
            
            .endpoint-card {
                background: #f8fafc;
                border: 1.5px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            
            .endpoint-card:hover {
                border-color: #0b69ff;
                box-shadow: 0 10px 25px rgba(11, 105, 255, 0.1);
                transform: translateY(-5px);
            }
            
            .endpoint-method {
                display: inline-block;
                background: #e0e7ff;
                color: #0550d9;
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
                margin-bottom: 10px;
            }
            
            .endpoint-method.post {
                background: #fef3c7;
                color: #d97706;
            }
            
            .endpoint-path {
                font-family: 'Courier New', monospace;
                font-size: 14px;
                color: #1e293b;
                margin-bottom: 8px;
                word-break: break-all;
            }
            
            .endpoint-description {
                font-size: 13px;
                color: #64748b;
                line-height: 1.5;
            }
            
            .cta-section {
                background: linear-gradient(135deg, #f0f9ff 0%, #f0f4ff 100%);
                border-radius: 12px;
                padding: 30px;
                text-align: center;
                margin-bottom: 20px;
            }
            
            .cta-section h3 {
                color: #1e293b;
                margin-bottom: 15px;
                font-size: 20px;
            }
            
            .button-group {
                display: flex;
                gap: 10px;
                justify-content: center;
                flex-wrap: wrap;
            }
            
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }
            
            .btn-primary {
                background: linear-gradient(135deg, #0b69ff 0%, #0550d9 100%);
                color: white;
                box-shadow: 0 4px 15px rgba(11, 105, 255, 0.3);
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(11, 105, 255, 0.4);
            }
            
            .btn-secondary {
                background: white;
                color: #0b69ff;
                border: 2px solid #0b69ff;
            }
            
            .btn-secondary:hover {
                background: #f0f4ff;
            }
            
            .footer {
                background: #f8fafc;
                padding: 20px 40px;
                text-align: center;
                border-top: 1px solid #e2e8f0;
                font-size: 13px;
                color: #64748b;
            }
            
            .status-badge {
                display: inline-block;
                background: #dcfce7;
                color: #166534;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            
            @media (max-width: 768px) {
                .header h1 {
                    font-size: 36px;
                }
                
                .header {
                    padding: 40px 20px;
                }
                
                .content {
                    padding: 20px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛣️ SafeRide API</h1>
                <p>Crash-aware multi-route ranking service</p>
            </div>
            
            <div class="content">
                <div class="version">
                    <strong>Version:</strong> 1.0.0 | 
                    <strong>Status:</strong> <span class="status-badge">✓ Operational</span>
                </div>
                
                <div class="cta-section">
                    <h3>Get Started</h3>
                    <div class="button-group">
                        <a href="/docs" class="btn btn-primary">📚 Interactive API Docs</a>
                        <a href="/redoc" class="btn btn-secondary">📖 ReDoc Documentation</a>
                    </div>
                </div>
                
                <div class="endpoints">
                    <h2>📍 Available Endpoints</h2>
                    <div class="endpoint-grid">
                        <div class="endpoint-card">
                            <div class="endpoint-method">GET</div>
                            <div class="endpoint-path">/health</div>
                            <div class="endpoint-description">Health check endpoint - verify API is running</div>
                        </div>
                        
                        <div class="endpoint-card">
                            <div class="endpoint-method">GET</div>
                            <div class="endpoint-path">/version</div>
                            <div class="endpoint-description">Get API version information</div>
                        </div>
                        
                        <div class="endpoint-card">
                            <div class="endpoint-method post">POST</div>
                            <div class="endpoint-path">/routes/rank</div>
                            <div class="endpoint-description">Rank multiple routes by crash risk and return WKT geometries</div>
                        </div>
                        
                        <div class="endpoint-card">
                            <div class="endpoint-method post">POST</div>
                            <div class="endpoint-path">/routes/rank_fc</div>
                            <div class="endpoint-description">Rank routes and return as GeoJSON FeatureCollection</div>
                        </div>
                        
                        <div class="endpoint-card">
                            <div class="endpoint-method">GET</div>
                            <div class="endpoint-path">/docs</div>
                            <div class="endpoint-description">Interactive Swagger UI - test endpoints live</div>
                        </div>
                        
                        <div class="endpoint-card">
                            <div class="endpoint-method">GET</div>
                            <div class="endpoint-path">/redoc</div>
                            <div class="endpoint-description">Alternative ReDoc documentation view</div>
                        </div>
                    </div>
                </div>
                
                <div class="cta-section">
                    <h3>🎯 Example Request</h3>
                    <pre style="background: #1e293b; color: #e2e8f0; padding: 15px; border-radius: 8px; text-align: left; overflow-x: auto; font-size: 12px;">curl -X POST https://saferide-alb-dev-356118384.us-west-2.elb.amazonaws.com/routes/rank \\
  -H "Content-Type: application/json" \\
  -d '{
    "start": [-105.0, 39.7],
    "end": [-104.99, 39.75],
    "buffer_m": 60,
    "max_alternatives": 3,
    "mode": "driving",
    "use_fixture": false
  }'</pre>
                </div>
            </div>
            
            <div class="footer">
                <p>🚀 Deployed on AWS ECS + RDS PostgreSQL with PostGIS | Crash-aware routing powered by OSRM</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"ok": True}

@app.get("/version")
def version():
    """Get API version"""
    return {"version": app.version}

# Routes
app.include_router(rank_router, prefix="/routes", tags=["routes"])
