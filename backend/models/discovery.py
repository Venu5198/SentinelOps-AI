from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class DiscoverySource(str, Enum):
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    PROMETHEUS_SD = "prometheus_sd"
    HTTP_PROBE = "http_probe"


class DiscoveryStatus(str, Enum):
    DISCOVERED = "discovered"
    APPROVED = "approved"
    IGNORED = "ignored"


class DiscoveredServiceItem(BaseSchema):
    id: str = Field(validation_alias="_id")
    name: str
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    image: Optional[str] = None
    source: DiscoverySource
    detected_endpoints: List[str] = []
    detected_health_path: str = "/health"
    status: DiscoveryStatus = DiscoveryStatus.DISCOVERED
    labels: Dict[str, str] = {}
    suggested_project_id: Optional[str] = None
    discovered_at: datetime = Field(default_factory=get_utc_now)
