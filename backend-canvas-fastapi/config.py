"""
Application configuration using Pydantic Settings.
Follows FastAPI best practices for settings management.
"""

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # CORS configuration
    # Production: Set CORS_ORIGINS env var to comma-separated list of allowed origins
    # Example: CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
    # Development: Defaults to ["*"] for local development convenience
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins. Use '*' for development only. Set via CORS_ORIGINS env var for production.",
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    @property
    def parsed_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS from comma-separated string if provided as env var."""
        if isinstance(self.cors_origins, str):
            return [
                origin.strip()
                for origin in self.cors_origins.split(",")
                if origin.strip()
            ]
        return self.cors_origins

    # Canvas API configuration (optional defaults)
    canvas_base_url: Optional[str] = None
    canvas_api_token: Optional[str] = None
    canvas_course_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("CANVAS_COURSE_ID", "COURSE_ID"),
    )

    # Logging configuration
    log_level: str = "INFO"

    # Application metadata
    app_name: str = "Canvas TA Dashboard API"
    app_version: str = "2.0.0"
    canvas_api_version: str = "1.0"

    # Performance settings
    thread_pool_max_workers: int = 20  # Increased from 10 for better parallelization
    assignment_thread_pool_max_workers: int = (
        10  # Increased from 3 for faster Canvas API processing
    )
    request_timeout: int = 30

    # Cache settings (optimized for performance)
    ta_cache_ttl: int = 14400  # 4 hours TTL for TA groups (rarely change)
    assignment_cache_ttl: int = 900  # 15 minutes TTL for assignment stats
    cache_max_size: int = 100  # Maximum cache entries
    enable_caching: bool = True  # Can disable for testing
    stale_cache_extension: int = (
        7200  # 2 hours - serve stale data within this window while refreshing
    )

    # No inner Config in Pydantic v2; using model_config above


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses @lru_cache to create a singleton, following FastAPI best practices.
    """
    return Settings()
