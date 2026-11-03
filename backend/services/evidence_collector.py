import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from backend.core.config import settings
from backend.core.logger import logger
from backend.db.mongodb import get_database
from backend.models.evidence import EvidenceSource, EvidenceType, EvidenceResponse


async def collect_evidence_for_incident(incident_id: str, service_name: str) -> List[Dict[str, Any]]:
    """
    Collects multi-source diagnostic telemetry for the incident (FR-04, AC-05, AC-06).
    Gracefully handles unavailable sources by recording UNKNOWN / UNAVAILABLE.
    """
    db = get_database()
    now = datetime.now(timezone.utc)
    collected: List[Dict[str, Any]] = []

    # 1. Collect HTTP Health Probe Evidence
    health_evidence = await _collect_health_probe_evidence(incident_id, service_name, now)
    if health_evidence:
        collected.append(health_evidence)

    # 2. Collect Prometheus Metrics Evidence
    metrics_evidence = await _collect_prometheus_metrics(incident_id, service_name, now)
    if metrics_evidence:
        collected.extend(metrics_evidence)

    # 3. Collect Loki Logs Evidence
    logs_evidence = await _collect_loki_logs(incident_id, service_name, now)
    if logs_evidence:
        collected.append(logs_evidence)

    # Persist all collected evidence
    for ev in collected:
        await db.evidence.insert_one(ev)

    logger.info(f"Collected {len(collected)} evidence artifacts for incident {incident_id}")
    return collected


async def _collect_health_probe_evidence(incident_id: str, service_name: str, now: datetime) -> Dict[str, Any]:
    db = get_database()
    service = await db.services.find_one({"name": service_name})
    base_endpoint = f"{service['endpoint_url']}{service['health_endpoint']}" if service else f"http://localhost:8080/health"

    candidate_endpoints = [base_endpoint]
    if "localhost:8080" in base_endpoint:
        candidate_endpoints.append(f"http://payment-service:8080/health")
    elif "localhost:8081" in base_endpoint:
        candidate_endpoints.append(f"http://order-service:8081/health")
    elif "payment-service" in base_endpoint:
        candidate_endpoints.append(f"http://localhost:8080/health")
    elif "order-service" in base_endpoint:
        candidate_endpoints.append(f"http://localhost:8081/health")

    payload = {"endpoint": base_endpoint, "status": "UNKNOWN", "response_code": None, "error": None}
    async with httpx.AsyncClient(timeout=4.0) as client:
        for ep in candidate_endpoints:
            try:
                resp = await client.get(ep)
                payload["endpoint"] = ep
                payload["response_code"] = resp.status_code
                payload["response_body"] = resp.text[:500]
                payload["status"] = "HEALTHY" if resp.status_code == 200 else "UNHEALTHY"
                payload["error"] = None
                break
            except Exception as e:
                payload["status"] = "UNREACHABLE"
                payload["error"] = str(e)

    return {
        "_id": f"evi_{uuid.uuid4().hex[:10]}",
        "incident_id": incident_id,
        "source": EvidenceSource.HEALTH_CHECK.value,
        "evidence_type": EvidenceType.HTTP_PROBE.value,
        "name": f"Health check probe: {service_name}",
        "payload": payload,
        "summary": f"Health check returned {payload['status']} (code: {payload['response_code']})",
        "observed_at": now,
        "created_at": now
    }


async def _collect_prometheus_metrics(incident_id: str, service_name: str, now: datetime) -> List[Dict[str, Any]]:
    results = []
    prom_url = f"{settings.PROMETHEUS_URL}/api/v1/query"
    queries = [
        {"name": "http_error_rate_5xx", "query": f'sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[5m])) / sum(rate(http_requests_total{{job="{service_name}"}}[5m]))'},
        {"name": "request_latency_p95_seconds", "query": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service_name}"}}[5m])) by (le))'}
    ]

    for q in queries:
        ev_doc = {
            "_id": f"evi_{uuid.uuid4().hex[:10]}",
            "incident_id": incident_id,
            "source": EvidenceSource.PROMETHEUS.value,
            "evidence_type": EvidenceType.METRIC.value,
            "name": q["name"],
            "payload": {},
            "summary": "",
            "observed_at": now,
            "created_at": now
        }
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(prom_url, params={"query": q["query"]})
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    ev_doc["payload"] = data
                    ev_doc["summary"] = f"PromQL query {q['name']} succeeded"
                else:
                    ev_doc["payload"] = {"status": "DEGRADED", "code": res.status_code}
                    ev_doc["summary"] = f"Prometheus returned HTTP {res.status_code}"
        except Exception as e:
            # AC-06: Missing source is explicitly recorded
            ev_doc["payload"] = {"status": "UNAVAILABLE", "error": str(e)}
            ev_doc["summary"] = f"Prometheus unavailable: {e}"

        results.append(ev_doc)
    return results


async def _collect_loki_logs(incident_id: str, service_name: str, now: datetime) -> Dict[str, Any]:
    loki_url = f"{settings.LOKI_URL}/loki/api/v1/query_range"
    logql = f'{{service="{service_name}"}} |= "error"'
    ev_doc = {
        "_id": f"evi_{uuid.uuid4().hex[:10]}",
        "incident_id": incident_id,
        "source": EvidenceSource.LOKI.value,
        "evidence_type": EvidenceType.LOG.value,
        "name": f"Error log stream: {service_name}",
        "payload": {},
        "summary": "",
        "observed_at": now,
        "created_at": now
    }
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(loki_url, params={"query": logql, "limit": 50})
            if res.status_code == 200:
                ev_doc["payload"] = res.json().get("data", {})
                ev_doc["summary"] = "Log query returned recent error entries"
            else:
                ev_doc["payload"] = {"status": "DEGRADED", "code": res.status_code}
                ev_doc["summary"] = f"Loki returned HTTP {res.status_code}"
    except Exception as e:
        # AC-06: Missing source is explicitly recorded
        ev_doc["payload"] = {"status": "UNAVAILABLE", "error": str(e)}
        ev_doc["summary"] = f"Loki unavailable: {e}"

    return ev_doc

