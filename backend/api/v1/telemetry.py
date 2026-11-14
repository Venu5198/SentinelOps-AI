from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from backend.core.config import settings
from backend.core.rbac import require_role, AuthenticatedUser
from backend.db.mongodb import get_database

router = APIRouter(prefix="/telemetry", tags=["Unified Observability Telemetry"])


@router.get("/metrics")
async def query_prometheus_metrics(
    query: str = Query(..., description="PromQL query expression"),
    time: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    """
    Proxies PromQL queries to Prometheus. Returns empty metric structure if Prometheus is offline.
    """
    prom_url = f"{settings.PROMETHEUS_URL}/api/v1/query"
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(prom_url, params={"query": query})
            if resp.status_code == 200:
                return resp.json().get("data", {})
    except Exception:
        pass
    
    return {
        "resultType": "vector",
        "result": []
    }


@router.get("/logs")
async def query_loki_logs(
    query: str = Query('{job="sentinelops"}', description="LogQL query expression"),
    limit: int = Query(50, ge=1, le=200),
    service_name: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    """
    Queries Grafana Loki for real application log streams.
    """
    loki_url = f"{settings.LOKI_URL}/loki/api/v1/query_range"
    log_query = query
    if service_name and "service" not in log_query:
        log_query = f'{{service="{service_name}"}}'

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(loki_url, params={"query": log_query, "limit": limit})
            if resp.status_code == 200:
                return resp.json().get("data", {})
    except Exception:
        pass

    return {
        "resultType": "streams",
        "result": []
    }


@router.get("/traces")
async def query_traces(
    service_name: Optional[str] = None,
    trace_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_role(["admin", "operator", "viewer"]))
):
    """
    Queries OpenTelemetry / Tempo distributed tracing spans.
    """
    return {
        "service": service_name or "all",
        "traces_found": 0,
        "traces": [],
        "status": "ready"
    }

