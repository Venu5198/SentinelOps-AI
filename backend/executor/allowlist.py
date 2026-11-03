from typing import Any, Dict

# Hardcoded catalog of allowlisted remediation actions (FR-08, AC-11, AC-12)
# Any action not explicitly enumerated here is rejected with zero shell invocation.
ALLOWLISTED_ACTIONS: Dict[str, Dict[str, Any]] = {
    "service.restart_container": {
        "action_id": "service.restart_container",
        "description": "Restarts a registered application container via Docker Engine SDK",
        "target_type": "docker_container",
        "allowed_services": ["payment-service", "order-service", "auth-service"],
        "allowed_parameters": {},
        "risk_level": "MEDIUM",
        "timeout_seconds": 30,
        "requires_approval": True,
    },
    "service.health_check": {
        "action_id": "service.health_check",
        "description": "Executes HTTP health probe against target service health endpoint",
        "target_type": "http_probe",
        "allowed_services": ["payment-service", "order-service", "auth-service", "mongodb", "redis"],
        "allowed_parameters": {},
        "risk_level": "LOW",
        "timeout_seconds": 10,
        "requires_approval": False,
    },
    "cache.clear_service_key": {
        "action_id": "cache.clear_service_key",
        "description": "Deletes specific corrupted cache key from Redis",
        "target_type": "redis_command",
        "allowed_services": ["payment-service"],
        "allowed_parameters": {"key_pattern": str},
        "risk_level": "LOW",
        "timeout_seconds": 5,
        "requires_approval": True,
    },
}


def is_action_allowlisted(action_id: str, target_service: str) -> bool:
    action = ALLOWLISTED_ACTIONS.get(action_id)
    if not action:
        return False
    if target_service not in action.get("allowed_services", []):
        return False
    return True
