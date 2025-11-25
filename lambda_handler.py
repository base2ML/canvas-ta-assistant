"""
Lambda handler for Canvas TA Dashboard
Uses Mangum to adapt FastAPI for AWS Lambda
"""
from mangum import Mangum
from main import app

# Create Lambda handler
handler = Mangum(app, lifespan="off")
