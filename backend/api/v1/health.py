import asyncio
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from prometheus_client import Gauge

from backend.core.config import settings
from backend.db.mongodb import get_database, is_mongodb_mock
from backend.db.redis import get_redis, is_redis_mock

router = APIRouter(tags=["Health & Readiness"])
start_time = time.time()

DEPENDENCY_UP = Gauge(
    "sentinelops_dependency_up", "Availability status of upstream dependencies (1=healthy, 0=unhealthy)", ["dependency"]
)


@router.get("/health", status_code=status.HTTP_200_OK)
@router.get("/health/liveness", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness probe: verifies process is alive and responsive."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "uptime_seconds": round(time.time() - start_time, 2),
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/ai", status_code=status.HTTP_200_OK)
async def ai_health():
    """Checks live Ollama connectivity and configured model."""
    candidate_urls = [settings.OLLAMA_BASE_URL]
    if "host.docker.internal" in settings.OLLAMA_BASE_URL:
        candidate_urls.append("http://localhost:11434")
    elif "localhost" in settings.OLLAMA_BASE_URL or "127.0.0.1" in settings.OLLAMA_BASE_URL:
        candidate_urls.append("http://host.docker.internal:11434")
    candidate_urls = list(dict.fromkeys(candidate_urls))

    ollama_live = False
    active_url = None
    available_models = []

    async with httpx.AsyncClient(timeout=2.0) as client:
        for url in candidate_urls:
            try:
                res = await client.get(f"{url}/api/tags")
                if res.status_code == 200:
                    ollama_live = True
                    active_url = url
                    available_models = [m.get("name") for m in res.json().get("models", [])]
                    break
            except Exception:
                pass

    return {
        "status": "ready" if ollama_live else "fallback_active",
        "live_ollama": ollama_live,
        "endpoint": active_url,
        "configured_model": settings.OLLAMA_MODEL,
        "available_models": available_models,
        "mode": "Ollama Local Inference" if ollama_live else "Deterministic Diagnostic Engine",
    }


async def _check_mongodb(timeout_seconds: float = 2.0) -> Dict[str, Any]:
    """Check MongoDB connectivity with strict timeout."""
    try:
        if is_mongodb_mock():
            return {"status": "mock_connected", "healthy": True}
        db = get_database()
        if db is None:
            return {"status": "unhealthy", "healthy": False, "error": "Database client not initialized"}
        await asyncio.wait_for(db.client.admin.command("ping"), timeout=timeout_seconds)
        return {"status": "connected", "healthy": True}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "healthy": False, "error": f"Connection timeout after {timeout_seconds}s"}
    except Exception as e:
        # Strip potential credentials or connection strings
        error_type = type(e).__name__
        return {"status": "unhealthy", "healthy": False, "error": f"{error_type}: connection failed"}


async def _check_redis(timeout_seconds: float = 2.0) -> Dict[str, Any]:
    """Check Redis connectivity with strict timeout."""
    try:
        if is_redis_mock():
            return {"status": "mock_connected", "healthy": True}
        r = get_redis()
        if r is None:
            return {"status": "unhealthy", "healthy": False, "error": "Redis client not initialized"}
        await asyncio.wait_for(r.ping(), timeout=timeout_seconds)
        return {"status": "connected", "healthy": True}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "healthy": False, "error": f"Connection timeout after {timeout_seconds}s"}
    except Exception as e:
        error_type = type(e).__name__
        return {"status": "unhealthy", "healthy": False, "error": f"{error_type}: connection failed"}


async def _check_external_service(url: str, timeout_seconds: float = 1.5) -> Dict[str, Any]:
    """Non-blocking probe for telemetry dependencies."""
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            res = await client.get(url)
            if res.status_code in [200, 204]:
                return {"status": "connected", "healthy": True}
            return {"status": "degraded", "healthy": False, "status_code": res.status_code}
    except Exception:
        return {"status": "unavailable", "healthy": False}


@router.get("/ready", status_code=status.HTTP_200_OK)
@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness probe: validates critical dependencies (MongoDB and Redis).
    Reports telemetry and AI status without failing readiness when fallback is active.
    """
    # 1. Probe critical dependencies with timeout protection
    mongo_res, redis_res = await asyncio.gather(_check_mongodb(timeout_seconds=2.0), _check_redis(timeout_seconds=2.0))

    is_ready = mongo_res["healthy"] and redis_res["healthy"]

    # 2. Probe optional telemetry integrations non-blockingly
    prom_url = f"{settings.PROMETHEUS_URL.rstrip('/')}/-/healthy"
    loki_url = f"{settings.LOKI_URL.rstrip('/')}/ready"

    prom_res, loki_res = await asyncio.gather(_check_external_service(prom_url), _check_external_service(loki_url))

    # Update Prometheus reliability metrics
    try:
        DEPENDENCY_UP.labels(dependency="mongodb").set(1 if mongo_res["healthy"] else 0)
        DEPENDENCY_UP.labels(dependency="redis").set(1 if redis_res["healthy"] else 0)
        DEPENDENCY_UP.labels(dependency="prometheus").set(1 if prom_res["healthy"] else 0)
        DEPENDENCY_UP.labels(dependency="loki").set(1 if loki_res["healthy"] else 0)
    except Exception:
        pass

    # 3. Compile clean, safe response without secret exposure
    resp_data = {
        "ready": is_ready,
        "status": "ready" if is_ready else "unhealthy",
        "components": {
            "mongodb": mongo_res["status"],
            "redis": redis_res["status"],
        },
        "telemetry": {
            "prometheus": prom_res["status"],
            "loki": loki_res["status"],
        },
        "ai_engine": {
            "configured_model": settings.OLLAMA_MODEL,
            "fallback_enabled": settings.FALLBACK_TO_MOCK_AI,
        },
        "errors": {},
    }

    if not mongo_res["healthy"]:
        resp_data["errors"]["mongodb"] = mongo_res.get("error", "unhealthy")
    if not redis_res["healthy"]:
        resp_data["errors"]["redis"] = redis_res.get("error", "unhealthy")

    if not resp_data["errors"]:
        resp_data["errors"] = None

    if not is_ready:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=resp_data)
    return resp_data
