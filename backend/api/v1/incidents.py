from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from backend.core.rbac import get_current_user, require_role, AuthenticatedUser, UserRole
from backend.db.mongodb import get_database
from backend.models.incident import (
    IncidentCreate, IncidentUpdate, IncidentResponse, IncidentStatus, IncidentSeverity,
    is_valid_transition
)
from backend.services.audit_service import record_audit_log

router = APIRouter(prefix="/incidents", tags=["Incident Management & Lifecycle"])


@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status"),
    service_filter: Optional[str] = Query(None, alias="service"),
    severity_filter: Optional[str] = Query(None, alias="severity"),
    limit: int = Query(50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """List and filter incidents by status, service, and severity (FR-03, AC-04)."""
    db = get_database()
    query = {}
    if status_filter:
        query["status"] = status_filter
    if service_filter:
        query["service_name"] = service_filter
    if severity_filter:
        query["severity"] = severity_filter

    cursor = db.incidents.find(query).sort("detected_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [IncidentResponse(**doc) for doc in docs]


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve full incident details (AC-18)."""
    db = get_database()
    incident = await db.incidents.find_one({"_id": incident_id})
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found"
        )
    return IncidentResponse(**incident)


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
async def transition_incident_status(
    incident_id: str,
    update_data: IncidentUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["operator", "admin"]))
):
    """
    Validates and executes lifecycle state transitions according to PRD FR-03 state DAG.
    Rejects illegal state jumps with HTTP 400.
    """
    db = get_database()
    incident = await db.incidents.find_one({"_id": incident_id})
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found"
        )

    current_status = IncidentStatus(incident["status"])
    target_status = update_data.status

    if target_status and target_status != current_status:
        if not is_valid_transition(current_status, target_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state transition from '{current_status.value}' to '{target_status.value}'"
            )

    now = datetime.now(timezone.utc)
    set_fields = {"updated_at": now}

    if target_status:
        set_fields["status"] = target_status.value
        if target_status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
            set_fields["resolved_at"] = now

    if update_data.assigned_to is not None:
        set_fields["assigned_to"] = update_data.assigned_to

    if update_data.severity:
        set_fields["severity"] = update_data.severity.value

    await db.incidents.update_one({"_id": incident_id}, {"$set": set_fields})
    incident.update(set_fields)

    await record_audit_log(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        action="INCIDENT_STATUS_CHANGED",
        resource_type="incident",
        resource_id=incident_id,
        details={
            "old_status": current_status.value,
            "new_status": target_status.value if target_status else current_status.value,
            "comment": update_data.comment
        },
        request_ip=request.client.host if request.client else None
    )

    return IncidentResponse(**incident)

