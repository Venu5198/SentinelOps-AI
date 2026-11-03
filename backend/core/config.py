from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    PROJECT_NAME: str = "SentinelOps AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    USE_MOCK_DB: bool = False
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    # Security & Auth
    SECRET_KEY: str = "sentinelops_dev_secret_key_must_be_overridden_in_production_min_64_chars_length"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    APPROVAL_TOKEN_EXPIRE_MINUTES: int = 15

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "sentinelops"
    MONGODB_MIN_POOL_SIZE: int = 5
    MONGODB_MAX_POOL_SIZE: int = 50

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_LOCK_TIMEOUT_SECONDS: int = 10

    # AI / Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:latest"
    AI_INFERENCE_TIMEOUT_SECONDS: int = 45
    FALLBACK_TO_MOCK_AI: bool = True

    # Telemetry
    PROMETHEUS_URL: str = "http://localhost:9090"
    ALERTMANAGER_URL: str = "http://localhost:9093"
    LOKI_URL: str = "http://localhost:3100"

    # Monitored Sample Service
    PAYMENT_SERVICE_URL: str = "http://localhost:8080"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


settings = Settings()
