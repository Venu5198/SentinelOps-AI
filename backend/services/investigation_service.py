import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status

from backend.ai.llm_client import get_llm_client
from backend.ai.prompt_builder import build_investigation_prompt
from backend.core.logger import logger
from backend.db.mongodb import get_database
from backend.models.incident import IncidentStatus
from backend.models.investigation import InvestigationOutputSchema, InvestigationResponse
from backend.services.audit_service import record_audit_log
from backend.services.evidence_collector import collect_evidence_for_incident


async def execute_investigation(
    incident_id: str, actor_id: str, actor_role: str, request_ip: str = None
) -> InvestigationResponse:
    """
    Coordinates incident investigation:
    1. Collects fresh telemetry evidence if none exists.
    2. Builds sanitized prompt.
    3. Runs LLM inference.
    4. Validates Pydantic schema and evidence citations.
    5. Transitions incident to ROOT_CAUSE_IDENTIFIED and AWAITING_APPROVAL.
    6. Saves immutable investigation record and audit log.
    """
    db = get_database()
    incident = await db.incidents.find_one({"_id": incident_id})
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    # Fetch existing evidence or collect fresh
    evidence_cursor = db.evidence.find({"incident_id": incident_id})
    evidence_list = await evidence_cursor.to_list(length=100)

    if not evidence_list:
        evidence_list = await collect_evidence_for_incident(incident_id, incident["service_name"])

    # Update incident state to INVESTIGATING
    now = datetime.now(timezone.utc)
    await db.incidents.update_one(
        {"_id": incident_id}, {"$set": {"status": IncidentStatus.INVESTIGATING.value, "updated_at": now}}
    )

    prompt = build_investigation_prompt(incident, evidence_list)
    llm_client = get_llm_client()

    try:
        report: InvestigationOutputSchema = await llm_client.generate_investigation(prompt, incident, evidence_list)
    except Exception as e:
        logger.error(f"AI investigation failed for incident {incident_id}: {e}")
        # AC-08: AI failure fallback
        await db.incidents.update_one(
            {"_id": incident_id},
            {
                "$set": {
                    "status": IncidentStatus.INVESTIGATING.value,
                    "metadata.ai_error": str(e),
                    "metadata.ai_status": "FAILED",
                    "updated_at": now,
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Investigation service encountered an error: {e}",
        )

    investigation_id = f"inv_{uuid.uuid4().hex[:10]}"
    inv_doc = {
        "_id": investigation_id,
        "incident_id": incident_id,
        "model_name": "qwen2.5 / local-inference",
        "report": report.model_dump(),
        "status": "completed",
        "raw_prompt_tokens": len(prompt) // 4,
        "raw_completion_tokens": len(report.model_dump_json()) // 4,
        "error_message": None,
        "created_at": now,
    }
    await db.investigations.insert_one(inv_doc)

    # Automatically create pending approval if actions are proposed
    for act in report.recommended_actions:
        approval_id = f"appr_{uuid.uuid4().hex[:10]}"
        from backend.services.approval_service import compute_action_signature

        sig = compute_action_signature(act.action_id, act.target_service, act.parameters)
        from datetime import timedelta

        expires_at = now + timedelta(minutes=15)

        appr_doc = {
            "_id": approval_id,
            "incident_id": incident_id,
            "action_id": act.action_id,
            "action_signature": sig,
            "target_service": act.target_service,
            "parameters": act.parameters,
            "rationale": act.rationale,
            "risk_level": act.risk_level,
            "status": "PENDING",
            "requested_by": "sentinelops-ai",
            "approved_by": None,
            "decision_reason": None,
            "expires_at": expires_at,
            "created_at": now,
            "decided_at": None,
        }
        await db.approvals.insert_one(appr_doc)

    # Transition to AWAITING_APPROVAL if actions require approval, else ROOT_CAUSE_IDENTIFIED
    next_status = (
        IncidentStatus.AWAITING_APPROVAL if report.recommended_actions else IncidentStatus.ROOT_CAUSE_IDENTIFIED
    )
    await db.incidents.update_one({"_id": incident_id}, {"$set": {"status": next_status.value, "updated_at": now}})

    await record_audit_log(
        actor_id=actor_id,
        actor_role=actor_role,
        action="AI_INVESTIGATION_COMPLETED",
        resource_type="investigation",
        resource_id=investigation_id,
        details={"confidence": report.confidence_score, "actions_count": len(report.recommended_actions)},
        request_ip=request_ip,
    )

    return InvestigationResponse(**inv_doc)
