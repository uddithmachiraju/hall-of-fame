from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Settings
    ENV: Literal["development", "production"] = Field(default="development", description="Application environment")
    APP_NAME: str = Field(default="ThrottleX", description="Name of the application")
    DEBUG: bool = Field(default=False, description="Debug mode")
    HOST: str = Field(default="0.0.0.0", description="Host to run the application on")
    PORT: int = Field(default=8000, description="Port to run the application on")
    APP_BASE_URL: str = Field(default="http://localhost:8000", description="Base URL for the application")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")

    # Observability Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get application settings with caching."""
    return Settings()


settings: Settings = get_settings()
