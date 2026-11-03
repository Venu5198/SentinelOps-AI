from datetime import datetime

from pydantic import Field

from backend.core.rbac import UserRole
from backend.models.common import BaseSchema


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
