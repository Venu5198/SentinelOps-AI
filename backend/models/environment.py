from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"


class EnvironmentCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=50)
    slug: str = Field(min_length=2, max_length=50)
    description: Optional[str] = None
    env_type: EnvironmentType = EnvironmentType.DEVELOPMENT
    project_id: str


class EnvironmentResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    name: str
    slug: str
    description: Optional[str] = None
    env_type: EnvironmentType
    project_id: str
    created_at: datetime = Field(default_factory=get_utc_now)
    services_count: int = 0
