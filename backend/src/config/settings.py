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
    APP_VERSION: str = Field(default="0.1.0", description="Application version")

    # Database Settings
    MONGO_URI: str = Field(default=..., description="MongoDB connection URI")

    # Email Verification Settings
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USE_TLS: bool = Field(default=True, description="Whether to use TLS for SMTP connection")
    SMTP_USERNAME: str = Field(default=..., description="SMTP server username")
    SMTP_PASSWORD: str = Field(default=..., description="SMTP server password")
    SMTP_FROM_EMAIL: str = Field(default=..., description="Email address used as the sender for outgoing emails")
    EMAIL_VERIFY_EXPIRE_HOURS: int = Field(
        default=24, description="Expiration time for email verification tokens in hours"
    )

    # Authentication Settings
    JWT_SECRET_KEY: str = Field(default=..., description="Secret key for JWT token generation")
    JWT_ALGORITHM: str = Field(default="HS256", description="Algorithm used for JWT token generation")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, description="Access token expiration time in minutes")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration time in days")

    # Observability Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get application settings with caching."""
    return Settings()


settings: Settings = get_settings()
