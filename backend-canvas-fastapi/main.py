"""
Canvas TA Dashboard FastAPI Application
Refactored to follow FastAPI best practices with dependency injection and modular routing.
"""

import os
import sys
from pathlib import Path
from typing import Annotated, Any, Dict

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import Settings, get_settings
from routers import (
    assignments,
    auth,
    cache,
    distribution,
    health,
    late_days,
    peer_reviews,
    statistics,
    submissions,
    ta_management,
)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure loguru for the application
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss A} | {level: <8} | {name}:{function}:{line} | {message}",
    colorize=True,
)
logger.add(
    "logs/canvas-ta-dashboard.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss A} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    enqueue=True,  # Thread-safe logging
)


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    Following best practices for application factory pattern.
    """
    # Get settings for app configuration
    settings = get_settings()

    # Create FastAPI app with settings-based configuration
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A FastAPI backend for tracking Canvas LMS assignment grading status and TA management",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS middleware using settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Include routers with dependency injection
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(assignments.router)
    app.include_router(submissions.router)
    app.include_router(statistics.router)
    app.include_router(distribution.router)
    app.include_router(ta_management.router)
    app.include_router(peer_reviews.router)
    app.include_router(late_days.router)
    app.include_router(cache.router)

    # Mount static files for React frontend (served at root "/")
    # Static directory is created during Docker build
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
        logger.info(f"Mounted static files from {static_dir}")
    else:
        logger.warning(f"Static directory not found at {static_dir}. Running in API-only mode.")

    return app


# Create the FastAPI application instance
app = create_application()

# Log application startup
logger.info("Canvas TA Dashboard FastAPI application initialized with loguru logging")


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
