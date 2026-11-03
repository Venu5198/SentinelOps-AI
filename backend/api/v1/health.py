import time
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from backend.core.config import settings
from backend.db.mongodb import get_database, is_mongodb_mock
from backend.db.redis import get_redis, is_redis_mock

router = APIRouter(tags=["Health & Readiness"])
start_time = time.time()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness probe: verifies process is alive and responsive."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "uptime_seconds": round(time.time() - start_time, 2),
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/ai", status_code=status.HTTP_200_OK)
async def ai_health():
    """Checks live Ollama connectivity and configured model."""
    import httpx
    candidate_urls = [
        "http://192.168.65.254:11434",
        settings.OLLAMA_BASE_URL,
        "http://host.docker.internal:11434",
        "http://localhost:11434"
    ]
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
        "mode": "Ollama Local Inference" if ollama_live else "Deterministic Diagnostic Engine"
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness probe: validates database and cache connectivity."""
    db_status = "unknown"
    redis_status = "unknown"
    is_ready = True
    errors = {}

    # Check MongoDB
    try:
        db = get_database()
        # Ping check
        if is_mongodb_mock():
            db_status = "mock_connected"
        else:
            await db.client.admin.command('ping')
            db_status = "connected"
    except Exception as e:
        db_status = "unhealthy"
        errors["mongodb"] = str(e)
        is_ready = False

    # Check Redis
    try:
        r = get_redis()
        await r.ping()
        redis_status = "mock_connected" if is_redis_mock() else "connected"
    except Exception as e:
        redis_status = "unhealthy"
        errors["redis"] = str(e)
        is_ready = False

    resp_data = {
        "ready": is_ready,
        "status": "ready" if is_ready else "degraded",
        "components": {
            "mongodb": db_status,
            "redis": redis_status,
        },
        "errors": errors if errors else None
    }

    if not is_ready:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=resp_data)
    return resp_data

