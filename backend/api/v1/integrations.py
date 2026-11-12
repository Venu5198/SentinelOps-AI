import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from backend.core.rbac import require_role, AuthenticatedUser
from backend.db.mongodb import get_database
from backend.models.integration import (
    IntegrationCreate,
    IntegrationResponse,
    IntegrationStatus,
    IntegrationType
)
from backend.services.audit_service import record_audit_log

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    project_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    db = get_database()
    query = {}
    if project_id:
        query["$or"] = [{"project_id": project_id}, {"project_id": None}]
    
    docs = await db.integrations.find(query).to_list(length=100)
    return docs


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integ_in: IntegrationCreate,
    current_user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    db = get_database()
    integ_id = f"integ_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    
    doc = {
        "_id": integ_id,
        "name": integ_in.name,
        "integration_type": integ_in.integration_type.value,
        "endpoint_url": integ_in.endpoint_url.rstrip("/"),
        "project_id": integ_in.project_id,
        "organization_id": integ_in.organization_id,
        "status": IntegrationStatus.UNTESTED.value,
        "last_checked_at": None,
        "last_error": None,
        "metadata": integ_in.metadata or {},
        "created_at": now
    }
    await db.integrations.insert_one(doc)

    await record_audit_log(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        action="INTEGRATION_CREATED",
        resource_type="integration",
        resource_id=integ_id,
        details={"name": integ_in.name, "type": integ_in.integration_type.value}
    )
    return doc


@router.post("/{integration_id}/test", response_model=IntegrationResponse)
async def test_integration_connection(
    integration_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator"]))
):
    db = get_database()
    integ = await db.integrations.find_one({"_id": integration_id})
    if not integ:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    target_url = integ["endpoint_url"]
    test_path = ""
    integ_type = integ["integration_type"]
    
    if integ_type == IntegrationType.PROMETHEUS.value:
        test_path = "/-/healthy"
    elif integ_type == IntegrationType.ALERTMANAGER.value:
        test_path = "/-/healthy"
    elif integ_type == IntegrationType.LOKI.value:
        test_path = "/ready"
    elif integ_type == IntegrationType.TEMPO.value:
        test_path = "/ready"
    else:
        test_path = ""

    probe_target = f"{target_url}{test_path}" if test_path else target_url
    status_result = IntegrationStatus.CONNECTED.value
    err_msg = None

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(probe_target)
            if resp.status_code >= 400:
                status_result = IntegrationStatus.DEGRADED.value
                err_msg = f"HTTP {resp.status_code}"
    except Exception as e:
        status_result = IntegrationStatus.DISCONNECTED.value
        err_msg = str(e)[:100]

    now = datetime.now(timezone.utc)
    await db.integrations.update_one(
        {"_id": integration_id},
        {"$set": {
            "status": status_result,
            "last_checked_at": now,
            "last_error": err_msg
        }}
    )
    updated = await db.integrations.find_one({"_id": integration_id})
    return updated
