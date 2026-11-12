import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.core.rbac import require_role, AuthenticatedUser
from backend.db.mongodb import get_database
from backend.models.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectStatus
)
from backend.models.environment import EnvironmentResponse, EnvironmentCreate
from backend.services.audit_service import record_audit_log

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    organization_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    db = get_database()
    query = {}
    if organization_id:
        query["organization_id"] = organization_id

    projects = await db.projects.find(query).to_list(length=200)
    result = []
    for proj in projects:
        # compute statistics
        svc_count = await db.services.count_documents({"project_id": proj["_id"]})
        inc_count = await db.incidents.count_documents({
            "project_id": proj["_id"],
            "status": {"$nin": ["RESOLVED", "CLOSED"]}
        })
        degraded = await db.services.count_documents({
            "project_id": proj["_id"],
            "health_status": {"$in": ["degraded", "unhealthy"]}
        })
        proj["services_count"] = svc_count
        proj["active_incidents_count"] = inc_count
        proj["health_status"] = "unhealthy" if degraded > 0 or inc_count > 0 else "healthy"
        result.append(proj)
    return result


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator"]))
):
    db = get_database()
    # Check duplicate slug in same org
    existing = await db.projects.find_one({
        "organization_id": project_in.organization_id,
        "slug": project_in.slug
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with slug '{project_in.slug}' already exists in this organization"
        )
    
    proj_id = f"proj_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    doc = {
        "_id": proj_id,
        "name": project_in.name,
        "slug": project_in.slug,
        "description": project_in.description,
        "organization_id": project_in.organization_id,
        "status": ProjectStatus.ACTIVE.value,
        "created_at": now,
        "updated_at": now
    }
    await db.projects.insert_one(doc)

    # Automatically create standard environments: dev, staging, prod
    standard_envs = [
        {"slug": "development", "name": "Development", "env_type": "development"},
        {"slug": "staging", "name": "Staging", "env_type": "staging"},
        {"slug": "production", "name": "Production", "env_type": "production"}
    ]
    for env in standard_envs:
        await db.environments.insert_one({
            "_id": f"env_{proj_id}_{env['slug']}",
            "project_id": proj_id,
            "name": env["name"],
            "slug": env["slug"],
            "env_type": env["env_type"],
            "created_at": now
        })

    await record_audit_log(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        action="PROJECT_CREATED",
        resource_type="project",
        resource_id=proj_id,
        details={"name": project_in.name, "slug": project_in.slug}
    )

    doc["services_count"] = 0
    doc["active_incidents_count"] = 0
    doc["health_status"] = "healthy"
    return doc


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    db = get_database()
    proj = await db.projects.find_one({"_id": project_id})
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    svc_count = await db.services.count_documents({"project_id": proj["_id"]})
    inc_count = await db.incidents.count_documents({
        "project_id": proj["_id"],
        "status": {"$nin": ["RESOLVED", "CLOSED"]}
    })
    degraded = await db.services.count_documents({
        "project_id": proj["_id"],
        "health_status": {"$in": ["degraded", "unhealthy"]}
    })
    proj["services_count"] = svc_count
    proj["active_incidents_count"] = inc_count
    proj["health_status"] = "unhealthy" if degraded > 0 or inc_count > 0 else "healthy"
    return proj


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator"]))
):
    db = get_database()
    update_data = {k: v for k, v in project_update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    await db.projects.update_one(
        {"_id": project_id},
        {"$set": update_data}
    )
    proj = await db.projects.find_one({"_id": project_id})
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    await record_audit_log(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        action="PROJECT_UPDATED",
        resource_type="project",
        resource_id=project_id,
        details=update_data
    )
    svc_count = await db.services.count_documents({"project_id": proj["_id"]})
    inc_count = await db.incidents.count_documents({
        "project_id": proj["_id"],
        "status": {"$nin": ["RESOLVED", "CLOSED"]}
    })
    proj["services_count"] = svc_count
    proj["active_incidents_count"] = inc_count
    proj["health_status"] = "healthy"
    return proj


@router.get("/{project_id}/environments", response_model=List[EnvironmentResponse])
async def list_project_environments(
    project_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    db = get_database()
    envs = await db.environments.find({"project_id": project_id}).to_list(length=50)
    result = []
    for env in envs:
        count = await db.services.count_documents({"project_id": project_id, "environment": env["slug"]})
        env["services_count"] = count
        result.append(env)
    return result


@router.post("/{project_id}/environments", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_project_environment(
    project_id: str,
    env_in: EnvironmentCreate,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator"]))
):
    db = get_database()
    existing = await db.environments.find_one({"project_id": project_id, "slug": env_in.slug})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Environment slug already exists for project")
    
    env_id = f"env_{project_id}_{env_in.slug}"
    now = datetime.now(timezone.utc)
    doc = {
        "_id": env_id,
        "project_id": project_id,
        "name": env_in.name,
        "slug": env_in.slug,
        "description": env_in.description,
        "env_type": env_in.env_type.value,
        "created_at": now
    }
    await db.environments.insert_one(doc)
    doc["services_count"] = 0
    return doc
