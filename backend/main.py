import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from backend.core.config import settings
from backend.core.logger import logger, correlation_id_ctx
from backend.core.security import get_password_hash
from backend.db.mongodb import connect_to_mongodb, close_mongodb_connection, get_database
from backend.db.redis import connect_to_redis, close_redis_connection
from backend.models.user import UserRole
from backend.models.service import HealthStatus

# Import Routers
from backend.api.v1.health import router as health_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.services import router as services_router
from backend.api.v1.incidents import router as incidents_router
from backend.api.v1.alerts import router as alerts_router
from backend.api.v1.evidence import router as evidence_router
from backend.api.v1.investigations import router as investigations_router
from backend.api.v1.approvals import router as approvals_router
from backend.api.v1.remediations import router as remediations_router
from backend.api.v1.audit import router as audit_router
from backend.api.v1.reports import router as reports_router


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
                    "created_at": datetime.datetime.now(datetime.timezone.utc)
                }
                await db.users.insert_one(admin_doc)
                logger.info(f"Seeded initial admin account: {email_addr}")
            else:
                # Ensure password is AdminPass123!
                await db.users.update_one(
                    {"email": email_addr},
                    {"$set": {"password_hash": get_password_hash("AdminPass123!")}}
                )

        # 2. Seed Default Monitored Payment Service
        svc_count = await db.services.count_documents({})
        if svc_count == 0:
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            sample_services = [
                {
                    "_id": "svc_payment_001",
                    "name": "payment-service",
                    "environment": "local",
                    "endpoint_url": "http://localhost:8080",
                    "health_endpoint": "/health",
                    "metrics_endpoint": "/metrics",
                    "health_status": HealthStatus.HEALTHY.value,
                    "monitoring_enabled": True,
                    "last_check_at": now,
                    "created_at": now
                },
                {
                    "_id": "svc_order_002",
                    "name": "order-service",
                    "environment": "local",
                    "endpoint_url": "http://localhost:8081",
                    "health_endpoint": "/health",
                    "metrics_endpoint": "/metrics",
                    "health_status": HealthStatus.HEALTHY.value,
                    "monitoring_enabled": True,
                    "last_check_at": now,
                    "created_at": now
                }
            ]
            await db.services.insert_many(sample_services)
            logger.info("Seeded initial sample monitored services (payment-service, order-service)")
    except Exception as e:
        logger.warning(f"Initial data seed notice: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous AI-Powered IT Incident Management Platform API",
    lifespan=lifespan
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

