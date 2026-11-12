from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from backend.core.rbac import require_role, AuthenticatedUser
from backend.db.mongodb import get_database

router = APIRouter(prefix="/dashboard", tags=["Dashboards"])


@router.get("/global")
async def get_global_dashboard(
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    """
    Returns an aggregated multi-project operations overview.
    """
    db = get_database()
    
    total_orgs = await db.organizations.count_documents({})
    total_projects = await db.projects.count_documents({})
    total_services = await db.services.count_documents({})
    healthy_services = await db.services.count_documents({"health_status": "healthy"})
    degraded_services = await db.services.count_documents({"health_status": {"$in": ["degraded", "unhealthy"]}})
    
    active_incidents = await db.incidents.find(
        {"status": {"$nin": ["RESOLVED", "CLOSED"]}}
    ).sort("detected_at", -1).to_list(length=10)
    
    recent_investigations = await db.investigations.find({}).sort("created_at", -1).to_list(length=5)
    
    projects_cursor = db.projects.find({}).to_list(length=20)
    projects_summary = []
    for p in await projects_cursor:
        svc_cnt = await db.services.count_documents({"project_id": p["_id"]})
        inc_cnt = await db.incidents.count_documents({"project_id": p["_id"], "status": {"$nin": ["RESOLVED", "CLOSED"]}})
        projects_summary.append({
            "id": p["_id"],
            "name": p["name"],
            "slug": p["slug"],
            "services_count": svc_cnt,
            "active_incidents": inc_cnt,
            "status": "unhealthy" if inc_cnt > 0 else "healthy"
        })

    return {
        "summary": {
            "total_organizations": total_orgs,
            "total_projects": total_projects,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "degraded_services": degraded_services,
            "active_incidents_count": len(active_incidents)
        },
        "projects": projects_summary,
        "recent_incidents": active_incidents,
        "recent_investigations": recent_investigations
    }


@router.get("/project/{project_id}")
async def get_project_dashboard(
    project_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    """
    Returns telemetry, services, and active incidents for a specific project.
    """
    db = get_database()
    project = await db.projects.find_one({"_id": project_id})
    if not project:
        project = {"_id": project_id, "name": "Unknown Project"}

    services = await db.services.find({"project_id": project_id}).to_list(length=100)
    environments = await db.environments.find({"project_id": project_id}).to_list(length=20)
    incidents = await db.incidents.find({"project_id": project_id}).sort("detected_at", -1).to_list(length=20)
    
    healthy_cnt = sum(1 for s in services if s.get("health_status") == "healthy")
    degraded_cnt = sum(1 for s in services if s.get("health_status") in ["degraded", "unhealthy"])

    return {
        "project": project,
        "environments": environments,
        "services": services,
        "incidents": incidents,
        "metrics": {
            "total_services": len(services),
            "healthy_services": healthy_cnt,
            "degraded_services": degraded_cnt,
            "active_incidents": sum(1 for i in incidents if i.get("status") not in ["RESOLVED", "CLOSED"])
        }
    }
