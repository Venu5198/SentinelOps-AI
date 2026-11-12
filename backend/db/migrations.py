import datetime
import uuid
from backend.core.logger import logger


async def migrate_to_multi_project(db):
    """
    Ensures organizations, projects, and environments exist,
    and updates existing services, incidents, and approvals with project context.
    Strictly non-destructive.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Default Organization
    default_org_id = "org_default"
    existing_org = await db.organizations.find_one({"_id": default_org_id})
    if not existing_org:
        await db.organizations.insert_one({
            "_id": default_org_id,
            "name": "Default Organization",
            "slug": "default-org",
            "description": "Primary organization workspace",
            "created_at": now,
            "updated_at": now
        })
        logger.info(f"Seeded default organization: {default_org_id}")

    # 2. Default SentinelOps Project
    default_proj_id = "proj_sentinelops_default"
    existing_proj = await db.projects.find_one({"_id": default_proj_id})
    if not existing_proj:
        await db.projects.insert_one({
            "_id": default_proj_id,
            "name": "SentinelOps Core",
            "slug": "sentinelops-core",
            "description": "Core SentinelOps internal services and mock telemetry",
            "organization_id": default_org_id,
            "status": "active",
            "created_at": now,
            "updated_at": now
        })
        logger.info(f"Seeded default project: {default_proj_id}")

    # 3. Default Environments for SentinelOps Project
    environments = [
        {"slug": "local", "name": "Local Development", "env_type": "development"},
        {"slug": "staging", "name": "Staging Cluster", "env_type": "staging"},
        {"slug": "production", "name": "Production Fleet", "env_type": "production"}
    ]
    for env in environments:
        env_id = f"env_{default_proj_id}_{env['slug']}"
        existing_env = await db.environments.find_one({"_id": env_id})
        if not existing_env:
            await db.environments.insert_one({
                "_id": env_id,
                "project_id": default_proj_id,
                "name": env["name"],
                "slug": env["slug"],
                "env_type": env["env_type"],
                "created_at": now
            })

    # 4. Migrate any existing services missing project_id
    res_svc = await db.services.update_many(
        {"project_id": {"$exists": False}},
        {"$set": {"project_id": default_proj_id, "service_type": "backend_api"}}
    )
    if res_svc.modified_count > 0:
        logger.info(f"Migrated {res_svc.modified_count} existing services to project: {default_proj_id}")

    # 5. Migrate any existing incidents missing project_id
    res_inc = await db.incidents.update_many(
        {"project_id": {"$exists": False}},
        {"$set": {"project_id": default_proj_id, "environment": "local"}}
    )
    if res_inc.modified_count > 0:
        logger.info(f"Migrated {res_inc.modified_count} existing incidents to project: {default_proj_id}")

    # 6. Ensure indexes for multi-tenant queries
    await db.services.create_index([("project_id", 1), ("name", 1)])
    await db.incidents.create_index([("project_id", 1), ("status", 1)])
    await db.environments.create_index([("project_id", 1), ("slug", 1)], unique=True)
    await db.projects.create_index([("organization_id", 1), ("slug", 1)], unique=True)
    await db.integrations.create_index([("project_id", 1), ("integration_type", 1)])
    await db.discovered_services.create_index([("source", 1), ("status", 1)])
