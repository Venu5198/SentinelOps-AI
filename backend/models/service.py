from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import Field
from backend.models.common import BaseSchema, get_utc_now


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    BACKEND_API = "backend_api"
    FRONTEND = "frontend"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_BROKER = "message_broker"
    WORKER = "worker"
    EXTERNAL_API = "external_api"
    OTHER = "other"


class ServiceCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=50)
    project_id: str = "proj_sentinelops_default"
    environment: str = "local"
    service_type: ServiceType = ServiceType.BACKEND_API
    endpoint_url: str
    health_endpoint: str = "/health"
    metrics_endpoint: str = "/metrics"
    monitoring_enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


class ServiceResponse(BaseSchema):
    id: str = Field(validation_alias="_id")
    name: str
    project_id: str = "proj_sentinelops_default"
    environment: str
    service_type: ServiceType = ServiceType.BACKEND_API
    endpoint_url: str
    health_endpoint: str = "/health"
    metrics_endpoint: str = "/metrics"
    health_status: HealthStatus = HealthStatus.UNKNOWN
    monitoring_enabled: bool = True
    last_check_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
