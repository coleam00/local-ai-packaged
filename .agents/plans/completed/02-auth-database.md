# Stage 02: Authentication & Database

## Summary
Add SQLite database with SQLAlchemy, user model for authentication, and JWT-based auth endpoints. After this stage, the backend has a working auth system.

## Prerequisites
- Stage 01 completed (core modules)

## Deliverable
- SQLite database with User table
- JWT authentication endpoints (login, logout, me)
- First-run admin setup endpoint
- Password hashing with bcrypt

---

## Files to Create

```
management-ui/backend/
├── app/
│   ├── database.py              # SQLAlchemy setup
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py              # User model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── auth.py              # Pydantic schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # Dependencies
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── auth.py          # Auth endpoints
│   └── core/
│       └── security.py          # JWT, password hashing
```

Update `requirements.txt`:
```
docker>=7.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
pyjwt>=2.8.0
bcrypt>=4.1.0
fastapi>=0.109.0
uvicorn>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.6
```

---

## Task 1: Setup Database

**File**: `management-ui/backend/app/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings
import os

# Ensure data directory exists
os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite specific
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
```

---

## Task 2: Create User Model

**File**: `management-ui/backend/app/models/__init__.py`
```python
from .user import User

__all__ = ["User"]
```

**File**: `management-ui/backend/app/models/user.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base
import bcrypt

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

    def set_password(self, password: str):
        """Hash and set password."""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )
```

---

## Task 3: Implement Security Module

**File**: `management-ui/backend/app/core/security.py`

```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..config import settings

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict]:
    """Get current user from token, returns None if not authenticated."""
    if not credentials:
        return None
    try:
        return decode_token(credentials.credentials)
    except HTTPException:
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """Get current user from token, raises if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return decode_token(credentials.credentials)
```

---

## Task 4: Create Auth Schemas

**File**: `management-ui/backend/app/schemas/__init__.py`
```python
from .auth import *
```

**File**: `management-ui/backend/app/schemas/auth.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool

class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class SetupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

class SetupStatus(BaseModel):
    setup_required: bool
    has_admin: bool

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class MessageResponse(BaseModel):
    message: str
```

---

## Task 5: Create API Dependencies

**File**: `management-ui/backend/app/api/__init__.py`
```python
# API package
```

**File**: `management-ui/backend/app/api/deps.py`

```python
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
```

---

## Task 6: Create Auth Routes

**File**: `management-ui/backend/app/api/routes/__init__.py`
```python
from fastapi import APIRouter
from .auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
```

**File**: `management-ui/backend/app/api/routes/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from ...database import get_db
from ...models.user import User
from ...schemas.auth import (
    LoginRequest, LoginResponse, UserResponse,
    SetupRequest, SetupStatus, ChangePasswordRequest, MessageResponse
)
from ...core.security import create_access_token, get_current_user
from ..deps import get_current_db_user

router = APIRouter()

@router.get("/setup-status", response_model=SetupStatus)
def get_setup_status(db: Session = Depends(get_db)):
    """Check if initial setup is required."""
    admin_exists = db.query(User).filter(User.is_admin == True).first() is not None
    return SetupStatus(
        setup_required=not admin_exists,
        has_admin=admin_exists
    )

@router.post("/setup", response_model=LoginResponse)
def initial_setup(request: SetupRequest, db: Session = Depends(get_db)):
    """Create initial admin user. Only works if no admin exists."""
    # Check if admin already exists
    if db.query(User).filter(User.is_admin == True).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup already completed"
        )

    # Validate passwords match
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Check username not taken
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Create admin user
    user = User(username=request.username, is_admin=True)
    user.set_password(request.password)
    user.last_login = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    # Return token
    access_token = create_access_token(data={"sub": user.username})
    return LoginResponse(
        access_token=access_token,
        username=user.username,
        is_admin=user.is_admin
    )

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.username == request.username).first()

    if not user or not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token(data={"sub": user.username})
    return LoginResponse(
        access_token=access_token,
        username=user.username,
        is_admin=user.is_admin
    )

@router.post("/logout", response_model=MessageResponse)
def logout(token_data: dict = Depends(get_current_user)):
    """Logout current user (client should discard token)."""
    # JWT tokens are stateless, so we just return success
    # Client is responsible for discarding the token
    return MessageResponse(message="Logged out successfully")

@router.get("/me", response_model=UserResponse)
def get_current_user_info(user: User = Depends(get_current_db_user)):
    """Get current authenticated user info."""
    return user

@router.post("/change-password", response_model=MessageResponse)
def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db)
):
    """Change current user's password."""
    if not user.verify_password(request.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    user.set_password(request.new_password)
    db.commit()

    return MessageResponse(message="Password changed successfully")
```

---

## Task 7: Update Config

**File**: `management-ui/backend/app/config.py` (update)

```python
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
```

---

## Task 8: Create Main App

**File**: `management-ui/backend/app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .api.routes import api_router
from .config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Stack Management UI",
    description="Management interface for local-ai-packaged Docker stack",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:9000", "http://127.0.0.1:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
```

---

## Validation

### Start the Server
```bash
cd management-ui/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 9000
```

### Test Endpoints
```bash
# Health check
curl http://localhost:9000/api/health

# Check setup status (should require setup)
curl http://localhost:9000/api/auth/setup-status

# Create admin user
curl -X POST http://localhost:9000/api/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpass123", "confirm_password": "adminpass123"}'

# Login
curl -X POST http://localhost:9000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpass123"}'

# Get current user (use token from login response)
curl http://localhost:9000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Check setup status again (should show has_admin: true)
curl http://localhost:9000/api/auth/setup-status
```

### Success Criteria
- [ ] Server starts without errors
- [ ] `/api/health` returns healthy status
- [ ] `/api/auth/setup-status` shows setup_required: true initially
- [ ] `/api/auth/setup` creates admin user and returns token
- [ ] `/api/auth/login` authenticates and returns token
- [ ] `/api/auth/me` returns user info with valid token
- [ ] Invalid token returns 401

---

## Next Stage
Proceed to `03-service-management-api.md` to add service control endpoints.
