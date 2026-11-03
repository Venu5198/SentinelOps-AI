from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class RootCauseHypothesis(BaseSchema):
    hypothesis: str
    likelihood: str = Field(description="'high', 'medium', or 'low'")
    explanation: str
    cited_evidence_ids: List[str] = Field(default_factory=list, description="IDs of evidence supporting this claim")


class ProposedAction(BaseSchema):
    action_id: str = Field(description="Must match allowlisted action identifier")
    action_name: str
    target_service: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str
    risk_level: str = Field(default="MEDIUM", description="'LOW', 'MEDIUM', 'HIGH'")
    requires_approval: bool = True


class InvestigationOutputSchema(BaseSchema):
    incident_summary: str
    affected_service: str
    observed_symptoms: List[str]
    probable_root_causes: List[RootCauseHypothesis]
    confidence_score: float = Field(ge=0.0, le=1.0)
    uncertainty_notes: Optional[str] = None
    recommended_actions: List[ProposedAction] = Field(default_factory=list)


class InvestigationResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    incident_id: str
    model_name: str
    report: InvestigationOutputSchema
    status: str = "completed"
    raw_prompt_tokens: Optional[int] = None
    raw_completion_tokens: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
