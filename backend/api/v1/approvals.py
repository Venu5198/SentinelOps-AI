from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from backend.core.rbac import get_current_user, require_role, AuthenticatedUser
from backend.db.mongodb import get_database
from backend.models.approval import ApprovalResponse, ApprovalDecision, ApprovalStatus
from backend.services.approval_service import process_approval_decision

router = APIRouter(prefix="/approvals", tags=["Human Approvals & Gates"])


@router.get("", response_model=List[ApprovalResponse])
async def list_approvals(
    incident_id: str = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """List pending or historical approvals."""
    db = get_database()
    query = {}
    if incident_id:
        query["incident_id"] = incident_id
    cursor = db.approvals.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=50)
    return [ApprovalResponse(**d) for d in docs]


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    db = get_database()
    doc = await db.approvals.find_one({"_id": approval_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    return ApprovalResponse(**doc)


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: str,
    decision_in: ApprovalDecision,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["operator", "admin"]))  # AC-09
):
    """
    Operator or Admin approves or rejects proposed remediation (FR-07, AC-09, AC-10).
    """
    return await process_approval_decision(
        approval_id=approval_id,
        decision=decision_in.decision,
        reason=decision_in.reason or "",
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        request_ip=request.client.host if request.client else None
    )

