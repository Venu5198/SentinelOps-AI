from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    MAINTENANCE = "maintenance"


class ProjectBase(BaseSchema):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=100)
    description: Optional[str] = None
    organization_id: str = "org_default"


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectResponse(ProjectBase):
    id: str = Field(validation_alias="_id")
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    services_count: int = 0
    active_incidents_count: int = 0
    health_status: str = "healthy"
