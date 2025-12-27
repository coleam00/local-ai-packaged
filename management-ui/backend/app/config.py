import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings


def get_default_compose_path() -> str:
    """Get the default compose path based on the platform and script location."""
    # First check environment variable
    if "COMPOSE_BASE_PATH" in os.environ:
        return os.environ["COMPOSE_BASE_PATH"]

    # Try to find the path relative to this file
    # The backend is at: management-ui/backend/app/config.py
    # The compose files are at: local-ai-packaged/docker-compose.yml
    current_file = Path(__file__).resolve()

    # Go up from config.py -> app -> backend -> management-ui -> local-ai-packaged
    project_root = current_file.parent.parent.parent.parent

    # Check if docker-compose.yml exists at this path
    if (project_root / "docker-compose.yml").exists():
        return str(project_root)

    # Fallback paths
    if sys.platform == "win32":
        # Common Windows paths
        candidates = [
            Path("C:/Temp/local-ai-packaged"),
            Path.home() / "local-ai-packaged",
        ]
    else:
        # Linux/Mac paths
        candidates = [
            Path("/opt/local-ai-packaged"),
            Path.home() / "local-ai-packaged",
        ]

    for candidate in candidates:
        if candidate.exists() and (candidate / "docker-compose.yml").exists():
            return str(candidate)

    # Return the detected project root anyway (best guess)
    return str(project_root)


class Settings(BaseSettings):
    # Paths
    COMPOSE_BASE_PATH: str = get_default_compose_path()
    COMPOSE_PROJECT_NAME: str = "localai"

    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./data/management.db")

    # Security
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = int(os.environ.get("PORT", "8001"))
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Log the detected path for debugging
if settings.DEBUG:
    print(f"COMPOSE_BASE_PATH: {settings.COMPOSE_BASE_PATH}")
