import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from backend.api.v1.alerts import router as alerts_router
from backend.api.v1.approvals import router as approvals_router
from backend.api.v1.audit import router as audit_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.evidence import router as evidence_router

# Import Routers
from backend.api.v1.health import router as health_router
from backend.api.v1.incidents import router as incidents_router
from backend.api.v1.investigations import router as investigations_router
from backend.api.v1.remediations import router as remediations_router
from backend.api.v1.reports import router as reports_router
from backend.api.v1.services import router as services_router
from backend.core.config import settings
from backend.core.logger import correlation_id_ctx, logger
from backend.core.security import get_password_hash
from backend.db.mongodb import close_mongodb_connection, connect_to_mongodb
from backend.db.redis import close_redis_connection, connect_to_redis
from backend.models.service import HealthStatus
from backend.models.user import UserRole


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB and Redis
    logger.info("Initializing SentinelOps AI backend...")
    db = await connect_to_mongodb()
    await connect_to_redis()

    # Seed default Admin and sample Services if empty
    await _seed_initial_data(db)

    logger.info("SentinelOps AI backend initialization complete")
    yield

    # Shutdown: Clean up connections
    logger.info("Shutting down SentinelOps AI backend...")
    await close_mongodb_connection()
    await close_redis_connection()


async def _seed_initial_data(db):
    try:
        # 1. Seed Default Admin Accounts
        for email_addr in ["admin@sentinelops.local", "admin@sentinelops.com"]:
            existing = await db.users.find_one({"email": email_addr})
            if not existing:
                import datetime

                admin_doc = {
                    "_id": f"user_admin_{uuid.uuid4().hex[:8]}",
                    "email": email_addr,
                    "password_hash": get_password_hash("AdminPass123!"),
                    "role": UserRole.ADMIN.value,
                    "is_active": True,
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                }
                await db.users.insert_one(admin_doc)
                logger.info(f"Seeded initial admin account: {email_addr}")
            else:
                # Ensure password is AdminPass123!
                await db.users.update_one(
                    {"email": email_addr}, {"$set": {"password_hash": get_password_hash("AdminPass123!")}}
                )

        # 2. Seed / Sync Monitored Services (payment-service, order-service)
        now = datetime.datetime.now(datetime.timezone.utc)
        services_specs = [
            {
                "_id": "svc_payment_001",
                "name": "payment-service",
                "environment": "production" if settings.ENVIRONMENT == "production" else "local",
                "endpoint_url": settings.PAYMENT_SERVICE_URL,
                "health_endpoint": "/health",
                "metrics_endpoint": "/metrics",
                "health_status": HealthStatus.HEALTHY.value,
                "monitoring_enabled": True,
            },
            {
                "_id": "svc_order_002",
                "name": "order-service",
                "environment": "production" if settings.ENVIRONMENT == "production" else "local",
                "endpoint_url": settings.ORDER_SERVICE_URL,
                "health_endpoint": "/health",
                "metrics_endpoint": "/metrics",
                "health_status": HealthStatus.HEALTHY.value,
                "monitoring_enabled": True,
            },
        ]
        for spec in services_specs:
            await db.services.update_one(
                {"name": spec["name"]},
                {
                    "$set": {
                        "endpoint_url": spec["endpoint_url"],
                        "health_endpoint": spec["health_endpoint"],
                        "metrics_endpoint": spec["metrics_endpoint"],
                        "environment": spec["environment"],
                        "monitoring_enabled": True,
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "_id": spec["_id"],
                        "name": spec["name"],
                        "health_status": HealthStatus.HEALTHY.value,
                        "created_at": now,
                    },
                },
                upsert=True,
            )
        logger.info("Synced monitored services in database (payment-service, order-service)")
    except Exception as e:
        logger.warning(f"Initial data seed notice: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous AI-Powered IT Incident Management Platform API",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Correlation ID Middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID") or f"req_{uuid.uuid4().hex[:12]}"
    token = correlation_id_ctx.set(corr_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response
    finally:
        correlation_id_ctx.reset(token)


# Register Root Health Checks
app.include_router(health_router)


# Prometheus Metrics Endpoint
@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Register Versioned API Routers
api_v1_prefix = "/api/v1"
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(services_router, prefix=api_v1_prefix)
app.include_router(incidents_router, prefix=api_v1_prefix)
app.include_router(alerts_router, prefix=api_v1_prefix)
app.include_router(evidence_router, prefix=api_v1_prefix)
app.include_router(investigations_router, prefix=api_v1_prefix)
app.include_router(approvals_router, prefix=api_v1_prefix)
app.include_router(remediations_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)
app.include_router(reports_router, prefix=api_v1_prefix)
