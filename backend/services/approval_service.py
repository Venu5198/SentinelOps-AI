import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from backend.core.config import settings
from backend.db.mongodb import get_database
from backend.models.approval import ApprovalResponse, ApprovalStatus
from backend.services.audit_service import record_audit_log


def compute_action_signature(
    action_id: str, target_service: str, parameters: Dict[str, Any], secret_key: Optional[str] = None
) -> str:
    """
    Computes a keyed HMAC-SHA256 signature binding the exact action, target service, and canonical parameters.
    Prevents parameter tampering and unauthorized offline signature generation.
    """
    key = (secret_key or settings.SECRET_KEY).encode("utf-8")
    canonical = json.dumps(parameters or {}, sort_keys=True)
    raw = f"{action_id}:{target_service}:{canonical}".encode("utf-8")
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


def verify_action_signature(
    signature: str, action_id: str, target_service: str, parameters: Dict[str, Any], secret_key: Optional[str] = None
) -> bool:
    """Constant-time verification of keyed HMAC-SHA256 signature against timing attacks."""
    expected = compute_action_signature(action_id, target_service, parameters, secret_key)
    return hmac.compare_digest(expected, signature)


async def process_approval_decision(
    approval_id: str, decision: ApprovalStatus, reason: str, actor_id: str, actor_role: str, request_ip: str = None
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
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Approval request is already in status '{appr['status']}'"
        )

    now = datetime.now(timezone.utc)

    # Check expiration (AC-11)
    expires_at = appr["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        await db.approvals.update_one({"_id": approval_id}, {"$set": {"status": ApprovalStatus.EXPIRED.value}})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval request has expired")

    set_fields = {"status": decision.value, "approved_by": actor_id, "decision_reason": reason, "decided_at": now}
    await db.approvals.update_one({"_id": approval_id}, {"$set": set_fields})
    appr.update(set_fields)

    # If rejected, update incident
    if decision == ApprovalStatus.REJECTED:
        await db.incidents.update_one(
            {"_id": appr["incident_id"]},
            {"$set": {"status": "FAILED", "updated_at": now, "metadata.rejection_reason": reason}},
        )

    await record_audit_log(
        actor_id=actor_id,
        actor_role=actor_role,
        action=f"REMEDIATION_{decision.value}",
        resource_type="approval",
        resource_id=approval_id,
        details={"reason": reason, "action_id": appr["action_id"], "target": appr["target_service"]},
        request_ip=request_ip,
    )

    return ApprovalResponse(**appr)
