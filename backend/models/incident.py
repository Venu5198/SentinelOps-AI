from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator
from backend.models.common import BaseSchema, get_utc_now


class IncidentSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


# Valid state transitions graph (FR-03)
VALID_TRANSITIONS: Dict[IncidentStatus, List[IncidentStatus]] = {
    IncidentStatus.DETECTED: [
        IncidentStatus.ACKNOWLEDGED,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.CLOSED
    ],
    IncidentStatus.ACKNOWLEDGED: [
        IncidentStatus.INVESTIGATING,
        IncidentStatus.ESCALATED,
        IncidentStatus.CLOSED
    ],
    IncidentStatus.INVESTIGATING: [
        IncidentStatus.ROOT_CAUSE_IDENTIFIED,
        IncidentStatus.FAILED,
        IncidentStatus.ESCALATED
    ],
    IncidentStatus.ROOT_CAUSE_IDENTIFIED: [
        IncidentStatus.AWAITING_APPROVAL,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.ESCALATED
    ],
    IncidentStatus.AWAITING_APPROVAL: [
        IncidentStatus.REMEDIATING,
        IncidentStatus.FAILED,
        IncidentStatus.ESCALATED
    ],
    IncidentStatus.REMEDIATING: [
        IncidentStatus.VERIFYING,
        IncidentStatus.FAILED
    ],
    IncidentStatus.VERIFYING: [
        IncidentStatus.RESOLVED,
        IncidentStatus.FAILED,
        IncidentStatus.ESCALATED
    ],
    IncidentStatus.FAILED: [
        IncidentStatus.INVESTIGATING,
        IncidentStatus.AWAITING_APPROVAL,
        IncidentStatus.ESCALATED,
        IncidentStatus.CLOSED
    ],
    IncidentStatus.ESCALATED: [
        IncidentStatus.INVESTIGATING,
        IncidentStatus.AWAITING_APPROVAL,
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED
    ],
    IncidentStatus.RESOLVED: [
        IncidentStatus.CLOSED,
        IncidentStatus.DETECTED  # In case of recurring bounce
    ],
    IncidentStatus.CLOSED: []
}


def is_valid_transition(current: IncidentStatus, target: IncidentStatus) -> bool:
    return target in VALID_TRANSITIONS.get(current, [])


class IncidentCreate(BaseSchema):
    fingerprint: str
    service_name: str
    severity: IncidentSeverity = IncidentSeverity.HIGH
    title: str
    description: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)


class IncidentUpdate(BaseSchema):
    status: Optional[IncidentStatus] = None
    assigned_to: Optional[str] = None
    severity: Optional[IncidentSeverity] = None
    comment: Optional[str] = None


class IncidentResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    fingerprint: str
    service_name: str
    severity: IncidentSeverity
    status: IncidentStatus
    title: str
    description: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    occurrence_count: int = 1
    assigned_to: Optional[str] = None
    detected_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
