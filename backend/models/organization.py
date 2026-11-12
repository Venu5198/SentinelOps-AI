from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class OrganizationBase(BaseSchema):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=100)
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    id: str = Field(validation_alias="_id")
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    projects_count: int = 0
