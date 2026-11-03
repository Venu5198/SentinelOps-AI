from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ApprovalCreate(BaseSchema):
    incident_id: str
    action_id: str
    target_service: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str
    risk_level: str
    expires_in_minutes: int = 15


class ApprovalDecision(BaseSchema):
    decision: ApprovalStatus = Field(description="'APPROVED' or 'REJECTED'")
    reason: Optional[str] = None


class ApprovalResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    incident_id: str
    action_id: str
    action_signature: str
    target_service: str
    parameters: Dict[str, Any]
    rationale: str
    risk_level: str
    status: ApprovalStatus
    requested_by: str
    approved_by: Optional[str] = None
    decision_reason: Optional[str] = None
    expires_at: datetime
    created_at: datetime
    decided_at: Optional[datetime] = None
