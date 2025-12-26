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
