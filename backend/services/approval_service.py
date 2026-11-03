import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import HTTPException, status
from backend.core.logger import logger
from backend.db.mongodb import get_database
from backend.models.approval import ApprovalResponse, ApprovalStatus
from backend.services.audit_service import record_audit_log


def compute_action_signature(action_id: str, target_service: str, parameters: Dict[str, Any]) -> str:
    """Computes deterministic SHA256 signature binding the exact action and parameters."""
    canonical = json.dumps(parameters or {}, sort_keys=True)
    raw = f"{action_id}:{target_service}:{canonical}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def process_approval_decision(
    approval_id: str,
    decision: ApprovalStatus,
    reason: str,
    actor_id: str,
    actor_role: str,
    request_ip: str = None
) -> ApprovalResponse:
    """
    Enforces human approval rules (FR-07, AC-09, AC-10, AC-11):
    - Validates unexpired status.
    - Records approving actor and reason.
    - Updates incident state if rejected or approved.
    """
    db = get_database()
    appr = await db.approvals.find_one({"_id": approval_id})
    if not appr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if appr["status"] != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval request is already in status '{appr['status']}'"
        )

    now = datetime.now(timezone.utc)

    # Check expiration (AC-11)
    if appr["expires_at"].replace(tzinfo=timezone.utc) < now:
        await db.approvals.update_one(
            {"_id": approval_id},
            {"$set": {"status": ApprovalStatus.EXPIRED.value}}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval request has expired"
        )

    set_fields = {
        "status": decision.value,
        "approved_by": actor_id,
        "decision_reason": reason,
        "decided_at": now
    }
    await db.approvals.update_one({"_id": approval_id}, {"$set": set_fields})
    appr.update(set_fields)

    # If rejected, update incident
    if decision == ApprovalStatus.REJECTED:
        await db.incidents.update_one(
            {"_id": appr["incident_id"]},
            {"$set": {"status": "FAILED", "updated_at": now, "metadata.rejection_reason": reason}}
        )

    await record_audit_log(
        actor_id=actor_id,
        actor_role=actor_role,
        action=f"REMEDIATION_{decision.value}",
        resource_type="approval",
        resource_id=approval_id,
        details={"reason": reason, "action_id": appr["action_id"], "target": appr["target_service"]},
        request_ip=request_ip
    )

    return ApprovalResponse(**appr)

