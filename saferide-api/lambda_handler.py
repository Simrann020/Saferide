"""
Lambda handler for FastAPI application using Mangum adapter.
This file should be in the root of the Lambda deployment package.
"""
from mangum import Mangum
from app.main import app

# Create the Lambda handler
handler = Mangum(app, lifespan="off")

# Optional: For async lifespan events, use:
# handler = Mangum(app)

