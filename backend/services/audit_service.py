import uuid
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from backend.db.mongodb import get_database
from backend.core.logger import logger, correlation_id_ctx
from backend.models.audit_log import AuditLogCreate, AuditLogResponse


async def record_audit_log(
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    result: str = "success",
    details: Optional[Dict[str, Any]] = None,
    request_ip: Optional[str] = None
) -> AuditLogResponse:
    db = get_database()
    corr_id = correlation_id_ctx.get("")
    log_doc = {
        "_id": f"audit_{uuid.uuid4().hex[:12]}",
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "result": result,
        "details": details or {},
        "request_ip": request_ip,
        "correlation_id": corr_id,
        "timestamp": datetime.now(timezone.utc)
    }
    try:
        await db.audit_logs.insert_one(log_doc)
        logger.info(f"Audit log recorded: {action} on {resource_type}/{resource_id} by {actor_id} ({result})")
    except Exception as e:
        logger.error(f"FAILED TO WRITE AUDIT LOG: {action} ({e})")
        raise e
    return AuditLogResponse(**log_doc)

