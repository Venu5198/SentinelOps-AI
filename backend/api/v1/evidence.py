from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from backend.core.rbac import get_current_user, AuthenticatedUser
from backend.db.mongodb import get_database
from backend.models.evidence import EvidenceResponse, EvidenceCreate
from backend.services.evidence_collector import collect_evidence_for_incident

router = APIRouter(prefix="/incidents/{incident_id}/evidence", tags=["Diagnostic Evidence"])


@router.get("", response_model=List[EvidenceResponse])
async def get_incident_evidence(
    incident_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve all diagnostic evidence collected for this incident (AC-05, AC-18)."""
    db = get_database()
    cursor = db.evidence.find({"incident_id": incident_id}).sort("observed_at", -1)
    docs = await cursor.to_list(length=100)
    return [EvidenceResponse(**d) for d in docs]


@router.post("/collect", response_model=List[EvidenceResponse])
async def trigger_evidence_collection(
    incident_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Triggers multi-source diagnostic evidence collection (FR-04)."""
    db = get_database()
    incident = await db.incidents.find_one({"_id": incident_id})
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    collected = await collect_evidence_for_incident(incident_id, incident["service_name"])
    return [EvidenceResponse(**c) for c in collected]

