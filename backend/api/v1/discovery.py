import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.core.rbac import require_role, AuthenticatedUser
from backend.db.mongodb import get_database
from backend.models.discovery import (
    DiscoveredServiceItem,
    DiscoverySource,
    DiscoveryStatus
)
from backend.models.service import ServiceCreate, HealthStatus
from backend.services.audit_service import record_audit_log

router = APIRouter(prefix="/discovery", tags=["Service Discovery"])


class ApproveDiscoveryRequest(BaseModel):
    project_id: str
    environment: str = "local"
    health_endpoint: str = "/health"
    endpoint_url: Optional[str] = None


@router.get("", response_model=List[DiscoveredServiceItem])
async def list_discovered_services(
    status_filter: Optional[DiscoveryStatus] = None,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    db = get_database()
    query = {}
    if status_filter:
        query["status"] = status_filter.value
    docs = await db.discovered_services.find(query).to_list(length=100)
    return docs


@router.post("/scan-docker", response_model=List[DiscoveredServiceItem])
async def trigger_docker_discovery(
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator"]))
):
    """
    Scans local Docker daemon via Docker socket (/var/run/docker.sock)
    Discovers running containers and extracts port mappings & names safely.
    """
    db = get_database()
    discovered_list = []
    now = datetime.now(timezone.utc)

    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list()
        
        for c in containers:
            c_name = c.name.lstrip("/")
            # Ignore internal sentinelops infrastructure from discovery
            if c_name.startswith("sentinelops-"):
                continue

            ports = c.ports or {}
            detected_endpoints = []
            for container_port, host_bindings in ports.items():
                if host_bindings:
                    host_port = host_bindings[0].get("HostPort")
                    detected_endpoints.append(f"http://host.docker.internal:{host_port}")

            item_id = f"disc_{c.short_id}"
            doc = {
                "_id": item_id,
                "name": c_name,
                "container_id": c.short_id,
                "container_name": c_name,
                "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                "source": DiscoverySource.DOCKER.value,
                "detected_endpoints": detected_endpoints,
                "detected_health_path": "/health",
                "status": DiscoveryStatus.DISCOVERED.value,
                "labels": c.labels or {},
                "suggested_project_id": "proj_sentinelops_default",
                "discovered_at": now
            }
            # Upsert into discovered_services
            await db.discovered_services.update_one(
                {"container_name": c_name},
                {"$set": doc},
                upsert=True
            )
            discovered_list.append(doc)

    except Exception:
        # Fallback if docker socket not available in test environment
        pass

    all_discovered = await db.discovered_services.find({"status": DiscoveryStatus.DISCOVERED.value}).to_list(length=100)
    return all_discovered


@router.post("/{discovery_id}/approve")
async def approve_discovered_service(
    discovery_id: str,
    approve_in: ApproveDiscoveryRequest,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator"]))
):
    db = get_database()
    disc = await db.discovered_services.find_one({"_id": discovery_id})
    if not disc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovered item not found")

    target_url = approve_in.endpoint_url or (disc["detected_endpoints"][0] if disc["detected_endpoints"] else "http://host.docker.internal:8000")
    
    # Register as official service
    service_id = f"svc_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    service_doc = {
        "_id": service_id,
        "name": disc["name"],
        "project_id": approve_in.project_id,
        "environment": approve_in.environment,
        "service_type": "backend_api",
        "endpoint_url": target_url.rstrip("/"),
        "health_endpoint": approve_in.health_endpoint,
        "metrics_endpoint": "/metrics",
        "health_status": HealthStatus.UNKNOWN.value,
        "monitoring_enabled": True,
        "last_check_at": None,
        "last_error": None,
        "created_at": now
    }
    await db.services.insert_one(service_doc)

    # Mark discovery as approved
    await db.discovered_services.update_one(
        {"_id": discovery_id},
        {"$set": {"status": DiscoveryStatus.APPROVED.value, "registered_service_id": service_id}}
    )

    await record_audit_log(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        action="DISCOVERY_APPROVED",
        resource_type="service",
        resource_id=service_id,
        details={"name": disc["name"], "project_id": approve_in.project_id}
    )
    return {"status": "approved", "service_id": service_id}
