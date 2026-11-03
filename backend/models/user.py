from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field
from backend.models.common import BaseSchema, get_utc_now
from backend.core.rbac import UserRole


class UserCreate(BaseSchema):
    email: str
    password: str = Field(min_length=8)
    role: UserRole = UserRole.VIEWER


class UserLogin(BaseSchema):
    email: str
    password: str


class UserResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    email: str
    role: UserRole
    is_active: bool = True
    created_at: datetime


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
