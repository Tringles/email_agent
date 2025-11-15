"""Environment variables and configuration."""

from pydantic_settings import BaseSettings
from typing import Optional, Literal
from enum import Enum


class Environment(str, Enum):
    """Application environment types."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"  # Default to dev
    DEBUG: bool = True  # Default to True for dev
    
    # Database - MySQL (Local Development)
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "email_agent"
    DB_CHARSET: str = "utf8mb4"
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct MySQL database URL."""
        # Use pymysql driver for MySQL
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )
    
    # Vector Database
    VECTOR_DB_URL: Optional[str] = None
    VECTOR_DB_API_KEY: Optional[str] = None
    
    # Storage
    AWS_S3_BUCKET: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    
    # LLM
    OPENAI_API_KEY: Optional[str] = None
    
    # Email Providers
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    NAVER_IMAP_USER: Optional[str] = None
    NAVER_IMAP_PASSWORD: Optional[str] = None
    
    # Celery (Local Development)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Email AI Aggregator"
    API_BASE_URL: str = "http://localhost:8000"  # Base URL for OAuth redirects
    
    # JWT
    JWT_SECRET_KEY: Optional[str] = None  # Set in .env
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Logging
    @property
    def LOG_LEVEL(self) -> str:
        """Get log level based on environment."""
        return "DEBUG" if self.DEBUG else "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
