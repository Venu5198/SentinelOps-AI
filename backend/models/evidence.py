from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class EvidenceSource(str, Enum):
    PROMETHEUS = "prometheus"
    LOKI = "loki"
    HEALTH_CHECK = "health_check"
    DOCKER = "docker"
    MANUAL = "manual"


class EvidenceType(str, Enum):
    METRIC = "metric"
    LOG = "log"
    HTTP_PROBE = "http_probe"
    CONTAINER_EVENT = "container_event"


class EvidenceCreate(BaseSchema):
    incident_id: str
    source: EvidenceSource
    evidence_type: EvidenceType
    name: str
    payload: Any
    observed_at: datetime = Field(default_factory=get_utc_now)
    summary: Optional[str] = None


class EvidenceResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    incident_id: str
    source: EvidenceSource
    evidence_type: EvidenceType
    name: str
    payload: Any
    observed_at: datetime
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
