from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class IntegrationType(str, Enum):
    PROMETHEUS = "prometheus"
    LOKI = "loki"
    ALERTMANAGER = "alertmanager"
    TEMPO = "tempo"
    OTEL_COLLECTOR = "otel_collector"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    UNTESTED = "untested"


class IntegrationCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=100)
    integration_type: IntegrationType
    endpoint_url: str
    project_id: Optional[str] = None  # None indicates organization/global scope
    organization_id: str = "org_default"
    credentials: Optional[Dict[str, str]] = None  # e.g. token, basic auth
    metadata: Optional[Dict[str, Any]] = None


class IntegrationResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    name: str
    integration_type: IntegrationType
    endpoint_url: str
    project_id: Optional[str] = None
    organization_id: str
    status: IntegrationStatus = IntegrationStatus.UNTESTED
    last_checked_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
