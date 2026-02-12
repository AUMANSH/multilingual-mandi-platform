"""
Configuration management for the Multilingual Mandi Platform.

This module handles all application configuration using Pydantic Settings
for type safety and validation.
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")
    reload: bool = Field(default=False, description="Enable auto-reload")
    
    # Security
    secret_key: str = Field(..., description="JWT signing secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="JWT token expiration time"
    )
    
    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")
    test_database_url: Optional[str] = Field(
        default=None, description="Test database URL"
    )
    
    # Redis
    redis_url: str = Field(..., description="Redis connection URL")
    test_redis_url: Optional[str] = Field(default=None, description="Test Redis URL")
    redis_cache_ttl: int = Field(default=3600, description="Default cache TTL")
    translation_cache_ttl: int = Field(
        default=86400, description="Translation cache TTL"
    )
    price_cache_ttl: int = Field(default=900, description="Price cache TTL")
    
    # Elasticsearch
    elasticsearch_url: str = Field(..., description="Elasticsearch cluster URL")
    elasticsearch_index_prefix: str = Field(
        default="mandi_platform", description="Index prefix"
    )
    
    # External APIs
    google_translate_api_key: Optional[str] = Field(
        default=None, description="Google Translate API key"
    )
    market_data_api_key: Optional[str] = Field(
        default=None, description="Market data API key"
    )
    
    # Languages
    supported_languages: List[str] = Field(
        default=["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"],
        description="Supported language codes"
    )
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # File Storage
    upload_dir: str = Field(default="uploads", description="Upload directory")
    max_file_size: int = Field(default=10485760, description="Max file size in bytes")
    
    # Notification
    sms_api_key: Optional[str] = Field(default=None, description="SMS API key")
    email_smtp_host: Optional[str] = Field(default=None, description="SMTP host")
    email_smtp_port: int = Field(default=587, description="SMTP port")
    email_username: Optional[str] = Field(default=None, description="Email username")
    email_password: Optional[str] = Field(default=None, description="Email password")
    
    @validator("supported_languages", pre=True)
    def parse_languages(cls, v):
        """Parse comma-separated language string into list."""
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",") if lang.strip()]
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins string into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_url(test: bool = False) -> str:
    """Get the appropriate database URL."""
    if test and settings.test_database_url:
        return settings.test_database_url
    return settings.database_url


def get_redis_url(test: bool = False) -> str:
    """Get the appropriate Redis URL."""
    if test and settings.test_redis_url:
        return settings.test_redis_url
    return settings.redis_url