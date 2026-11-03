from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from backend.models.common import BaseSchema, get_utc_now


class AuditLogCreate(BaseSchema):
    actor_id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    result: str = "success"
    details: Optional[Dict[str, Any]] = None
    request_ip: Optional[str] = None
    correlation_id: Optional[str] = None


class AuditLogResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    actor_id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    result: str
    details: Optional[Dict[str, Any]] = None
    request_ip: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=get_utc_now)
