"""
Lambda handler wrapper for FastAPI application
"""
from mangum import Mangum
from main import app

# Create the Mangum handler for AWS Lambda
handler = Mangum(app, lifespan="off")
