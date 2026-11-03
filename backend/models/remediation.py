from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFYING = "VERIFYING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


class RemediationExecutionCreate(BaseSchema):
    incident_id: str
    approval_id: str


class RemediationExecutionResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    incident_id: str
    approval_id: str
    action_id: str
    target_service: str
    parameters: Dict[str, Any]
    status: ExecutionStatus
    execution_result: Optional[Dict[str, Any]] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_details: Optional[Dict[str, Any]] = None
    executed_by: str
    executed_at: datetime
    completed_at: Optional[datetime] = None
