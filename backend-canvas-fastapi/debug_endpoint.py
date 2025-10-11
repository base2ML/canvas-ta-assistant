"""
Debug endpoint to test URL validation in production.
Temporary file to help diagnose the HttpUrl validation issue.
"""

from fastapi import APIRouter
from models import TAGradingRequest
from pydantic import ValidationError
import traceback

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.post("/test-validation")
async def test_validation(request_data: dict):
    """Test TAGradingRequest validation with the exact data from frontend."""
    try:
        # Try to create the TAGradingRequest object
        request = TAGradingRequest(**request_data)
        return {
            "status": "success",
            "message": "Validation passed",
            "processed_data": {
                "base_url": request.base_url,
                "api_token": "***" if request.api_token else None,
                "course_id": request.course_id
            }
        }
    except ValidationError as e:
        return {
            "status": "validation_error",
            "error": str(e),
            "details": e.errors(),
            "raw_data": request_data
        }
    except Exception as e:
        return {
            "status": "unexpected_error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "raw_data": request_data
        }