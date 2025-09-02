"""
Application configuration using Pydantic Settings.
Follows FastAPI best practices for settings management.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS configuration
    cors_origins: list[str] = ["*"]  # Should be restricted in production
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Canvas API configuration (optional defaults)
    canvas_base_url: Optional[str] = None
    canvas_api_token: Optional[str] = None

    # Logging configuration
    log_level: str = "INFO"

    # Application metadata
    app_name: str = "Canvas TA Dashboard API"
    app_version: str = "2.0.0"
    canvas_api_version: str = "1.0"

    # Performance settings
    thread_pool_max_workers: int = 10
    assignment_thread_pool_max_workers: int = 3  # Optimized for Canvas API
    request_timeout: int = 30

    # Cache settings (matching original performance)
    ta_cache_ttl: int = 3600  # 1 hour TTL for TA groups
    assignment_cache_ttl: int = 900  # 15 minutes TTL for assignment stats
    cache_max_size: int = 100  # Maximum cache entries
    enable_caching: bool = True  # Can disable for testing

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses @lru_cache to create a singleton, following FastAPI best practices.
    """
    return Settings()
