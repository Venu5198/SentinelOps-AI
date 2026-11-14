import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.core.rbac import require_role, AuthenticatedUser
from backend.db.mongodb import get_database
from backend.models.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse
)
from backend.services.audit_service import record_audit_log

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    db = get_database()
    cursor = db.organizations.find({})
    orgs = await cursor.to_list(length=100)
    
    result = []
    for org in orgs:
        # compute project count
        proj_count = await db.projects.count_documents({"organization_id": org["_id"]})
        org["projects_count"] = proj_count
        result.append(org)
    return result


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_in: OrganizationCreate,
    current_user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    db = get_database()
    existing = await db.organizations.find_one({"slug": org_in.slug})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with slug '{org_in.slug}' already exists"
        )
    
    org_id = f"org_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    doc = {
        "_id": org_id,
        "name": org_in.name,
        "slug": org_in.slug,
        "description": org_in.description,
        "created_at": now,
        "updated_at": now
    }
    await db.organizations.insert_one(doc)
    
    await record_audit_log(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        action="ORGANIZATION_CREATED",
        resource_type="organization",
        resource_id=org_id,
        details={"name": org_in.name, "slug": org_in.slug}
    )
    doc["projects_count"] = 0
    return doc


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    db = get_database()
    org = await db.organizations.find_one({"_id": organization_id})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    org["projects_count"] = await db.projects.count_documents({"organization_id": organization_id})
    return org


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    org_update: OrganizationUpdate,
    current_user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    db = get_database()
    update_data = {k: v for k, v in org_update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    await db.organizations.update_one(
        {"_id": organization_id},
        {"$set": update_data}
    )
    res = await db.organizations.find_one({"_id": organization_id})
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    res["projects_count"] = await db.projects.count_documents({"organization_id": organization_id})
    return res
