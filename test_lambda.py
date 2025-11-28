import json
import sys
sys.path.insert(0, '.')
from main import app, handler

# Test event simulating API Gateway POST /api/auth/login
event = {
    "version": "2.0",
    "routeKey": "$default",
    "rawPath": "/api/auth/login",
    "rawQueryString": "",
    "headers": {
        "content-type": "application/json",
        "host": "jt6ktzteab.execute-api.us-east-1.amazonaws.com"
    },
    "requestContext": {
        "http": {
            "method": "POST",
            "path": "/api/auth/login",
            "protocol": "HTTP/1.1",
            "sourceIp": "1.2.3.4"
        },
        "routeKey": "$default",
        "stage": "$default"
    },
    "body": json.dumps({"email": "test@example.com", "password": "test123"}),
    "isBase64Encoded": False
}

# Invoke the handler
result = handler(event, {})
print(json.dumps(result, indent=2))
