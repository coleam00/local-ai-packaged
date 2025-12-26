import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Paths
    COMPOSE_BASE_PATH: str = os.environ.get("COMPOSE_BASE_PATH", "/opt/local-ai-packaged")
    COMPOSE_PROJECT_NAME: str = "localai"

    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./data/management.db")

    # Security
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 9000
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
