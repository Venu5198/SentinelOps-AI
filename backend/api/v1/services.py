import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
import httpx
from backend.core.rbac import get_current_user, require_role, AuthenticatedUser, UserRole
from backend.db.mongodb import get_database
from backend.models.service import ServiceCreate, ServiceResponse, HealthStatus
from backend.services.audit_service import record_audit_log

router = APIRouter(prefix="/services", tags=["Services Registry & Monitoring"])


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def register_service(
    service_in: ServiceCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    db = get_database()
    existing = await db.services.find_one({"name": service_in.name})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service '{service_in.name}' is already registered"
        )
    service_id = f"service_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    service_doc = {
        "_id": service_id,
        "name": service_in.name,
        "environment": service_in.environment,
        "endpoint_url": service_in.endpoint_url.rstrip("/"),
        "health_endpoint": service_in.health_endpoint,
        "metrics_endpoint": service_in.metrics_endpoint,
        "health_status": HealthStatus.UNKNOWN.value,
        "monitoring_enabled": service_in.monitoring_enabled,
        "last_check_at": None,
        "last_error": None,
        "created_at": now
    }
    await db.services.insert_one(service_doc)

    await record_audit_log(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        action="SERVICE_REGISTERED",
        resource_type="service",
        resource_id=service_id,
        details={"service_name": service_in.name},
        request_ip=request.client.host if request.client else None
    )

    return ServiceResponse(**service_doc)


@router.get("", response_model=List[ServiceResponse])
async def list_services(current_user: AuthenticatedUser = Depends(get_current_user)):
    db = get_database()
    cursor = db.services.find().sort("name", 1)
    services = await cursor.to_list(length=100)
    return [ServiceResponse(**s) for s in services]


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    db = get_database()
    service = await db.services.find_one({"_id": service_id})
    if not service:
        service = await db.services.find_one({"name": service_id})
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return ServiceResponse(**service)


@router.post("/{service_id}/check-health", response_model=ServiceResponse)
async def probe_service_health(
    service_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Executes a real HTTP health probe against the target service endpoint."""
    db = get_database()
    service = await db.services.find_one({"_id": service_id})
    if not service:
        service = await db.services.find_one({"name": service_id})
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    target_url = f"{service['endpoint_url']}{service['health_endpoint']}"
    now = datetime.now(timezone.utc)
    status_val = HealthStatus.UNHEALTHY
    error_msg = None

    candidate_urls = [target_url]
    service.get("name", "")
    if "localhost:8080" in target_url:
        candidate_urls.append(f"http://payment-service:8080{service['health_endpoint']}")
    elif "localhost:8081" in target_url:
        candidate_urls.append(f"http://order-service:8081{service['health_endpoint']}")
    elif "payment-service" in target_url:
        candidate_urls.append(f"http://localhost:8080{service['health_endpoint']}")
    elif "order-service" in target_url:
        candidate_urls.append(f"http://localhost:8081{service['health_endpoint']}")

    async with httpx.AsyncClient(timeout=4.0) as client:
        for url in candidate_urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    status_val = HealthStatus.HEALTHY
                    error_msg = None
                    break
                elif resp.status_code < 500:
                    status_val = HealthStatus.DEGRADED
                    error_msg = f"HTTP {resp.status_code}"
                else:
                    status_val = HealthStatus.UNHEALTHY
                    error_msg = f"HTTP {resp.status_code}"
            except Exception as e:
                status_val = HealthStatus.UNHEALTHY
                error_msg = str(e)

    update_fields = {
        "health_status": status_val.value,
        "last_check_at": now,
        "last_error": error_msg
    }
    await db.services.update_one({"_id": service["_id"]}, {"$set": update_fields})
    service.update(update_fields)

    return ServiceResponse(**service)

