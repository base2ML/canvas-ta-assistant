"""
Lambda handler wrapper for FastAPI using Mangum
Handles ASGI to AWS Lambda event conversion
"""
from mangum import Mangum
from main import app

# Create Lambda handler
handler = Mangum(app, lifespan="off")
