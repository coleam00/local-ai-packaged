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
