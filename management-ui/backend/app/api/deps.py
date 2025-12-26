from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocal
from ..models.user import User
from ..core.security import get_current_user, get_current_user_optional
from ..core.docker_client import DockerClient
from ..core.compose_parser import ComposeParser
from ..core.dependency_graph import DependencyGraph
from ..core.env_manager import EnvManager
from ..config import settings

def get_docker_client() -> DockerClient:
    """Get Docker client instance."""
    return DockerClient(
        project=settings.COMPOSE_PROJECT_NAME,
        base_path=settings.COMPOSE_BASE_PATH
    )

def get_compose_parser() -> ComposeParser:
    """Get Compose parser instance."""
    return ComposeParser(settings.COMPOSE_BASE_PATH)

def get_dependency_graph(
    parser: ComposeParser = Depends(get_compose_parser)
) -> DependencyGraph:
    """Get dependency graph instance."""
    return DependencyGraph(parser)

def get_env_manager() -> EnvManager:
    """Get environment manager instance."""
    return EnvManager(settings.COMPOSE_BASE_PATH)

def get_current_db_user(
    db: Session = Depends(get_db),
    token_data: dict = Depends(get_current_user)
) -> User:
    """Get current authenticated user from database."""
    user = db.query(User).filter(User.username == token_data.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

def require_admin(
    user: User = Depends(get_current_db_user)
) -> User:
    """Require admin privileges."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user
