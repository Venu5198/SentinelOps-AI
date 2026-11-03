from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field
from backend.core.logger import logger
from backend.services.deduplication_service import process_incoming_alert
from backend.services.audit_service import record_audit_log

router = APIRouter(prefix="/alerts", tags=["Alertmanager Webhook & Ingestion"])


class AlertItem(BaseModel):
    status: str
    labels: Dict[str, str]
    annotations: Optional[Dict[str, str]] = Field(default_factory=dict)
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    fingerprint: Optional[str] = None


class AlertmanagerWebhookPayload(BaseModel):
    version: Optional[str] = "4"
    groupKey: Optional[str] = None
    status: str  # "firing" or "resolved"
    receiver: Optional[str] = None
    groupLabels: Optional[Dict[str, str]] = Field(default_factory=dict)
    commonLabels: Optional[Dict[str, str]] = Field(default_factory=dict)
    commonAnnotations: Optional[Dict[str, str]] = Field(default_factory=dict)
    alerts: List[AlertItem]


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def receive_alertmanager_webhook(payload: AlertmanagerWebhookPayload, request: Request):
    """
    Ingests Prometheus Alertmanager webhook payloads.
    Validates, classifies, deduplicates, and correlates incidents (FR-02, AC-01, AC-02, AC-03).
    """
    if not payload.alerts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Alertmanager payload must contain at least one alert item"
        )

    results = []
    for alert in payload.alerts:
        # Mandatory validation (AC-02)
        if not alert.labels.get("alertname"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Alert missing mandatory label: 'alertname'"
            )

        alert_dict = alert.model_dump()
        incident_doc, was_created = await process_incoming_alert(alert_dict)

        results.append({
            "incident_id": incident_doc["_id"],
            "service_name": incident_doc["service_name"],
            "status": incident_doc["status"],
            "was_created_new": was_created,
            "occurrence_count": incident_doc["occurrence_count"]
        })

        if was_created:
            await record_audit_log(
                actor_id="alertmanager",
                actor_role="system",
                action="INCIDENT_DETECTED",
                resource_type="incident",
                resource_id=incident_doc["_id"],
                details={"fingerprint": incident_doc["fingerprint"], "service": incident_doc["service_name"]},
                request_ip=request.client.host if request.client else None
            )

    return {
        "status": "success",
        "processed_count": len(results),
        "results": results
    }

