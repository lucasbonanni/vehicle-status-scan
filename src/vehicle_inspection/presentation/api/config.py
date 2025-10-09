"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/vehicle_inspection"
    database_test_url: str = "postgresql://postgres:password@localhost:5432/vehicle_inspection_test"

    # Security
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Application
    debug: bool = True
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # CORS
    allowed_origins: Union[str, List[str]] = "http://localhost:3000,http://localhost:8080"
    allowed_methods: Union[str, List[str]] = "GET,POST,PUT,DELETE,OPTIONS"
    allowed_headers: Union[str, List[str]] = "*"

    @model_validator(mode='after')
    def convert_cors_lists(self):
        """Convert comma-separated strings to lists."""
        if isinstance(self.allowed_origins, str):
            self.allowed_origins = [item.strip() for item in self.allowed_origins.split(",") if item.strip()]
        if isinstance(self.allowed_methods, str):
            self.allowed_methods = [item.strip() for item in self.allowed_methods.split(",") if item.strip()]
        if isinstance(self.allowed_headers, str):
            self.allowed_headers = [item.strip() for item in self.allowed_headers.split(",") if item.strip()]
        return self

    # Database Pool
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False
        env_ignore_empty = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
