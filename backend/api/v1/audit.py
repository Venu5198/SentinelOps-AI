from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.core.rbac import get_current_user, require_role, AuthenticatedUser
from backend.db.mongodb import get_database
from backend.models.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Logging & Compliance"])


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    action: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Query immutable audit log entries (FR-11, AC-16)."""
    db = get_database()
    query = {}
    if action:
        query["action"] = action
    if actor_id:
        query["actor_id"] = actor_id
    if resource_id:
        query["resource_id"] = resource_id

    cursor = db.audit_logs.find(query).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [AuditLogResponse(**d) for d in docs]


# Immutable Audit Trail Protection (FR-11, AC-16)
# Explicitly reject any mutation or deletion attempts against the audit repository
@router.post("", include_in_schema=False)
@router.put("", include_in_schema=False)
@router.patch("", include_in_schema=False)
@router.delete("", include_in_schema=False)
@router.delete("/{audit_id}", include_in_schema=False)
async def reject_audit_mutation():
    """Permanent rejection of any audit log modification or deletion."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Audit repository is strictly append-only. Modification and deletion operations are permanently forbidden by compliance policy."
    )

