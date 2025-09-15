"""
Authentication and credential validation endpoints.
Following FastAPI best practices for security and error handling.
"""

import asyncio
from typing import Annotated, Any, Dict

from canvasapi.exceptions import CanvasException, InvalidAccessToken
from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import (
    SettingsDep,
    ThreadPoolDep,
    validate_canvas_credentials,
    resolve_credentials,
)
from models import CanvasCredentials, CredentialValidationResponse, UserProfile

router = APIRouter(
    prefix="/api",
    tags=["authentication"],
    responses={401: {"description": "Invalid credentials"}},
)


@router.post("/validate-credentials", response_model=CredentialValidationResponse)
async def validate_credentials(
    credentials: CanvasCredentials, settings: SettingsDep, thread_pool: ThreadPoolDep
) -> CredentialValidationResponse:
    """
    Validate Canvas API credentials by attempting to fetch current user info.

    - **base_url**: Canvas instance base URL (e.g., https://canvas.institution.edu)
    - **api_token**: Canvas API access token

    Returns user profile information if credentials are valid.
    """
    try:
        base_url, token = resolve_credentials(
            credentials.base_url, credentials.api_token, settings
        )
        canvas = await validate_canvas_credentials(base_url, token, settings)

        # Get current user info
        loop = asyncio.get_event_loop()
        user = await loop.run_in_executor(
            thread_pool, lambda: canvas.get_current_user()
        )

        return CredentialValidationResponse(
            valid=True,
            user=UserProfile(
                id=user.id,
                name=user.name,
                email=getattr(user, "email", None),
                login_id=getattr(user, "login_id", None),
            ),
            error=None,
        )

    except HTTPException as e:
        # Re-raise HTTP exceptions (these are already properly formatted)
        return CredentialValidationResponse(valid=False, user=None, error=e.detail)
    except Exception as e:
        return CredentialValidationResponse(
            valid=False, user=None, error=f"Unexpected error: {str(e)}"
        )


@router.post("/test-connection")
async def test_connection(
    credentials: CanvasCredentials, settings: SettingsDep
) -> Dict[str, Any]:
    """
    Test basic connectivity to Canvas API without detailed validation.
    Lighter weight endpoint for connection testing.

    - **base_url**: Canvas instance base URL
    - **api_token**: Canvas API access token
    """
    try:
        base_url, token = resolve_credentials(
            credentials.base_url, credentials.api_token, settings
        )
        await validate_canvas_credentials(base_url, token, settings)

        return {
            "status": "success",
            "message": "Successfully connected to Canvas API",
            "base_url": base_url,
        }

    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"Connection test failed: {e.detail}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}",
        )
