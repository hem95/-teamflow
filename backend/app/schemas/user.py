from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
import re


class UserCreate(BaseModel):
    """Data required to register a new account."""
    email: EmailStr
    username: str
    display_name: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_-]{3,30}$", v):
            raise ValueError("Username must be 3-30 chars, lowercase letters/numbers/_ only")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long (max 72 bytes)")
        return v


class UserLogin(BaseModel):
    """Data required to log in."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """What we send back when returning user data — never includes the password."""
    id: int
    email: str
    username: str
    display_name: str
    avatar_url: Optional[str]
    is_online: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # lets us convert SQLAlchemy objects directly


class TokenResponse(BaseModel):
    """Returned after login/register — two tokens + user info."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str
