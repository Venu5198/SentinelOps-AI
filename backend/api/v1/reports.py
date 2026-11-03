from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from backend.core.rbac import get_current_user, AuthenticatedUser
from backend.db.mongodb import get_database

router = APIRouter(prefix="/reports", tags=["Incident Reports & Analytics"])


@router.get("/incidents/{incident_id}")
async def generate_incident_report(
    incident_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generates a complete post-incident report with timeline, evidence, AI diagnosis, approvals, and recovery (FR-12, AC-18)."""
    db = get_database()
    incident = await db.incidents.find_one({"_id": incident_id})
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    evidence = await db.evidence.find({"incident_id": incident_id}).to_list(length=100)
    investigations = await db.investigations.find({"incident_id": incident_id}).to_list(length=20)
    approvals = await db.approvals.find({"incident_id": incident_id}).to_list(length=20)
    executions = await db.remediation_executions.find({"incident_id": incident_id}).to_list(length=20)
    audit = await db.audit_logs.find({"resource_id": incident_id}).to_list(length=50)

    # Format Markdown Report
    md_lines = [
        f"# Incident Post-Mortem Report: {incident['_id']} - {incident['title']}",
        f"**Service:** {incident['service_name']} | **Severity:** {incident['severity'].upper()} | **Final Status:** {incident['status']}",
        f"**Detected At:** {incident['detected_at']} | **Resolved At:** {incident.get('resolved_at', 'Unresolved')}\n",
        "## 1. Executive Summary",
        f"{incident.get('description', '')}\n",
        "## 2. Diagnostic Evidence Collected",
        f"Total evidence items: {len(evidence)}"
    ]
    for ev in evidence:
        md_lines.append(f"- **[{ev['source'].upper()}]** {ev['name']}: {ev.get('summary', '')}")

    md_lines.append("\n## 3. AI Investigation & Root Cause")
    if investigations:
        inv = investigations[-1]
        rep = inv.get("report", {})
        md_lines.append(f"**Confidence:** {rep.get('confidence_score', 'N/A')}")
        md_lines.append(f"**Summary:** {rep.get('incident_summary', '')}")
        for rc in rep.get("probable_root_causes", []):
            md_lines.append(f"- **Hypothesis:** {rc.get('hypothesis')}")
            md_lines.append(f"  *Explanation:* {rc.get('explanation')}")
            md_lines.append(f"  *Evidence Citations:* {', '.join(rc.get('cited_evidence_ids', []))}")
    else:
        md_lines.append("No automated AI investigation was conducted.")

    md_lines.append("\n## 4. Remediation & Human Approval")
    for app in approvals:
        md_lines.append(f"- Action: `{app['action_id']}` on `{app['target_service']}` | Status: **{app['status']}** (by {app.get('approved_by') or 'N/A'})")

    md_lines.append("\n## 5. Execution & Recovery Verification")
    for ex in executions:
        md_lines.append(f"- Execution `{ex['_id']}`: Status **{ex['status']}**, Recovery Verification: **{ex['verification_status']}**")

    return {
        "incident": incident,
        "evidence_count": len(evidence),
        "evidence": evidence,
        "investigations": investigations,
        "approvals": approvals,
        "executions": executions,
        "audit_logs": audit,
        "markdown_report": "\n".join(md_lines)
    }

