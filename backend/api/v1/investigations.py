from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.core.rbac import AuthenticatedUser, get_current_user, require_role
from backend.db.mongodb import get_database
from backend.models.investigation import InvestigationResponse
from backend.services.investigation_service import execute_investigation

router = APIRouter(prefix="/incidents/{incident_id}/investigations", tags=["AI Investigation"])


@router.post("", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
async def trigger_investigation(
    incident_id: str, request: Request, current_user: AuthenticatedUser = Depends(require_role(["operator", "admin"]))
):
    """Triggers an AI-powered incident investigation (FR-05, AC-07, AC-08)."""
    return await execute_investigation(
        incident_id=incident_id,
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        request_ip=request.client.host if request.client else None,
    )


@router.get("", response_model=List[InvestigationResponse])
async def list_investigations(incident_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Lists all historical AI investigations for this incident."""
    db = get_database()
    cursor = db.investigations.find({"incident_id": incident_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=20)
    return [InvestigationResponse(**d) for d in docs]


@router.get("/latest", response_model=InvestigationResponse)
async def get_latest_investigation(incident_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves the most recent AI investigation report for this incident."""
    db = get_database()
    doc = await db.investigations.find_one({"incident_id": incident_id}, sort=[("created_at", -1)])
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No investigation found for this incident")
    return InvestigationResponse(**doc)
