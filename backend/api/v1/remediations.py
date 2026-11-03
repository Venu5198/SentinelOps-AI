from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from backend.core.rbac import get_current_user, require_role, AuthenticatedUser
from backend.db.mongodb import get_database
from backend.models.remediation import RemediationExecutionCreate, RemediationExecutionResponse
from backend.executor.restricted_executor import execute_approved_remediation

router = APIRouter(prefix="/remediations", tags=["Restricted Remediation Execution & Verification"])


@router.post("/execute", response_model=RemediationExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_remediation(
    req: RemediationExecutionCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["operator", "admin"]))
):
    """
    Executes an approved, allowlisted remediation action (FR-08, AC-11, AC-12, AC-13).
    """
    return await execute_approved_remediation(
        approval_id=req.approval_id,
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        request_ip=request.client.host if request.client else None
    )


@router.get("", response_model=List[RemediationExecutionResponse])
async def list_executions(
    incident_id: str = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    db = get_database()
    query = {}
    if incident_id:
        query["incident_id"] = incident_id
    cursor = db.remediation_executions.find(query).sort("executed_at", -1)
    docs = await cursor.to_list(length=50)
    return [RemediationExecutionResponse(**d) for d in docs]


@router.get("/{execution_id}", response_model=RemediationExecutionResponse)
async def get_execution(
    execution_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    db = get_database()
    doc = await db.remediation_executions.find_one({"_id": execution_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution record not found")
    return RemediationExecutionResponse(**doc)

