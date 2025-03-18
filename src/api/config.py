from pydantic_settings import BaseSettings
from typing import Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "E-commerce Analytics API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # Database Settings
    OLTP_DB_HOST: str = "postgres-oltp"
    OLTP_DB_PORT: int = 5432
    OLTP_DB_USER: str = "${OLTP_DB_USER}"
    OLTP_DB_PASSWORD: str = "${OLTP_DB_PASSWORD}"
    OLTP_DB_NAME: str = "ecommerce"
    
    OLAP_DB_HOST: str = "postgres-olap"
    OLAP_DB_PORT: int = 5433
    OLAP_DB_USER: str = "${OLAP_DB_USER}"
    OLAP_DB_PASSWORD: str = "${OLAP_DB_PASSWORD}"
    OLAP_DB_NAME: str = "ecommerce_analytics"
    
    # Redis Settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "${REDIS_PASSWORD}"
    REDIS_DB: int = 0
    
    # JWT Settings
    JWT_SECRET_KEY: str = "${JWT_SECRET_KEY}"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenTelemetry Settings
    OTEL_SERVICE_NAME: str = "ecommerce-analytics-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    SQL_ECHO: bool = False
    
    # Cache Settings
    CACHE_TTL: int = 300  # 5 minutes
    
    # Rate Limiting
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour
    RATE_LIMIT_MAX_REQUESTS: int = 1000
    
    # Feature Flags
    ENABLE_CACHING: bool = True
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_TELEMETRY: bool = True
    
    @property
    def OLTP_DATABASE_URL(self) -> str:
        """Generate OLTP database URL."""
        return (
            f"postgresql://{self.OLTP_DB_USER}:{self.OLTP_DB_PASSWORD}"
            f"@{self.OLTP_DB_HOST}:{self.OLTP_DB_PORT}/{self.OLTP_DB_NAME}"
        )
    
    @property
    def OLAP_DATABASE_URL(self) -> str:
        """Generate OLAP database URL."""
        return (
            f"postgresql://{self.OLAP_DB_USER}:{self.OLAP_DB_PASSWORD}"
            f"@{self.OLAP_DB_HOST}:{self.OLAP_DB_PORT}/{self.OLAP_DB_NAME}"
        )
    
    @property
    def REDIS_URL(self) -> str:
        """Generate Redis URL."""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Create cached instance of settings."""
    return Settings()

# Environment-specific configurations
def get_environment_settings() -> dict:
    """Get environment-specific settings."""
    env = os.getenv("ENVIRONMENT", "development")
    
    base_settings = {
        "development": {
            "DEBUG": True,
            "SQL_ECHO": True,
            "LOG_LEVEL": "DEBUG",
        },
        "staging": {
            "DEBUG": False,
            "SQL_ECHO": False,
            "LOG_LEVEL": "INFO",
        },
        "production": {
            "DEBUG": False,
            "SQL_ECHO": False,
            "LOG_LEVEL": "WARNING",
            "CORS_ORIGINS": [
                "https://api.ecommerce-analytics.com",
                "https://dashboard.ecommerce-analytics.com"
            ],
        }
    }
    
    return base_settings.get(env, base_settings["development"]) 