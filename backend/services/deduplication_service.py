import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from backend.core.logger import logger
from backend.db.mongodb import get_database
from backend.db.redis import acquire_distributed_lock, release_distributed_lock
from backend.models.incident import IncidentSeverity, IncidentStatus


def generate_fingerprint(service: str, alertname: str, severity: str) -> str:
    raw = f"{service.lower()}:{alertname.lower()}:{severity.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


async def process_incoming_alert(alert_data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Ingests and deduplicates an incoming alert.
    Returns (incident_doc, was_created_new).
    """
    db = get_database()
    labels = alert_data.get("labels", {})
    annotations = alert_data.get("annotations", {})

    service_name = labels.get("service") or labels.get("job", "unknown-service")
    alertname = labels.get("alertname", "UnknownAlert")
    raw_severity = labels.get("severity", "high").lower()

    # Map severity
    sev_map = {
        "critical": IncidentSeverity.CRITICAL,
        "high": IncidentSeverity.HIGH,
        "medium": IncidentSeverity.MEDIUM,
        "low": IncidentSeverity.LOW,
        "warning": IncidentSeverity.MEDIUM,
        "info": IncidentSeverity.INFO,
    }
    severity = sev_map.get(raw_severity, IncidentSeverity.HIGH)

    fingerprint = alert_data.get("fingerprint") or generate_fingerprint(service_name, alertname, raw_severity)

    # Acquire distributed lock on fingerprint to guarantee atomic deduplication
    lock_key = f"alert:dedup:{fingerprint}"
    await acquire_distributed_lock(lock_key, timeout_seconds=5)

    try:
        # Check for active non-closed incident with this fingerprint
        active_statuses = [
            IncidentStatus.DETECTED.value,
            IncidentStatus.ACKNOWLEDGED.value,
            IncidentStatus.INVESTIGATING.value,
            IncidentStatus.ROOT_CAUSE_IDENTIFIED.value,
            IncidentStatus.AWAITING_APPROVAL.value,
            IncidentStatus.REMEDIATING.value,
            IncidentStatus.VERIFYING.value,
            IncidentStatus.FAILED.value,
            IncidentStatus.ESCALATED.value,
        ]

        existing = await db.incidents.find_one({"fingerprint": fingerprint, "status": {"$in": active_statuses}})

        now = datetime.now(timezone.utc)

        if existing:
            # Update existing active incident (Deduplication AC-03)
            logger.info(f"Deduplicating alert for active incident {existing['_id']} (fingerprint: {fingerprint})")
            update_data = {
                "$inc": {"occurrence_count": 1},
                "$set": {"updated_at": now, "last_alert_payload": alert_data},
            }
            await db.incidents.update_one({"_id": existing["_id"]}, update_data)
            existing["occurrence_count"] += 1
            existing["updated_at"] = now
            return existing, False

        # Create new incident (AC-01)
        incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        title = annotations.get("summary") or f"{alertname} in {service_name}"
        desc = annotations.get("description") or f"Alertmanager alert {alertname} fired for service {service_name}"

        new_doc = {
            "_id": incident_id,
            "fingerprint": fingerprint,
            "service_name": service_name,
            "severity": severity.value,
            "status": IncidentStatus.DETECTED.value,
            "title": title,
            "description": desc,
            "labels": labels,
            "annotations": annotations,
            "occurrence_count": 1,
            "assigned_to": None,
            "detected_at": now,
            "updated_at": now,
            "resolved_at": None,
            "metadata": {"raw_alert": alert_data},
        }

        await db.incidents.insert_one(new_doc)
        logger.info(f"Created new incident {incident_id} for service {service_name}")
        return new_doc, True

    finally:
        await release_distributed_lock(lock_key)
