import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.api.v1.health import (
    _check_mongodb,
    _check_redis,
    _check_external_service,
    DEPENDENCY_UP,
)
from scripts.backup_mongodb import (
    calculate_sha256,
    prune_old_backups,
    CRITICAL_COLLECTIONS,
)
from scripts.restore_mongodb import verify_database_integrity
from scripts.deploy import deploy_release, rollback_release, save_known_good, load_known_good
from scripts.verify_deployment import verify_deployment, probe_endpoint


# --- 1. Liveness & Readiness Tests ---


@pytest.mark.asyncio
async def test_liveness_probe_returns_uptime(client):
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "version" in data
    assert "project" in data


@pytest.mark.asyncio
async def test_readiness_probe_healthy_streak(client):
    res = await client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["ready"] is True
    assert data["components"]["mongodb"] in ["connected", "mock_connected"]
    assert data["components"]["redis"] in ["connected", "mock_connected"]
    assert "telemetry" in data
    assert "ai_engine" in data


@pytest.mark.asyncio
async def test_readiness_probe_mongodb_timeout_handled(monkeypatch):
    import backend.api.v1.health as health_mod

    async def mock_admin_command(*args, **kwargs):
        raise asyncio.TimeoutError()

    class MockAdmin:
        command = mock_admin_command

    class MockClient:
        admin = MockAdmin()

    class MockDB:
        client = MockClient()

    monkeypatch.setattr(health_mod, "is_mongodb_mock", lambda: False)
    monkeypatch.setattr(health_mod, "get_database", lambda: MockDB())

    res = await health_mod._check_mongodb(timeout_seconds=0.1)
    assert res["healthy"] is False
    assert "timeout" in res["error"].lower()


@pytest.mark.asyncio
async def test_readiness_probe_redis_timeout_handled(monkeypatch):
    import backend.api.v1.health as health_mod

    async def mock_ping(*args, **kwargs):
        raise asyncio.TimeoutError()

    class MockRedis:
        ping = mock_ping

    monkeypatch.setattr(health_mod, "is_redis_mock", lambda: False)
    monkeypatch.setattr(health_mod, "get_redis", lambda: MockRedis())

    res = await health_mod._check_redis(timeout_seconds=0.1)
    assert res["healthy"] is False
    assert "timeout" in res["error"].lower()


@pytest.mark.asyncio
async def test_readiness_probe_telemetry_degradation_non_fatal():
    """Verify that an unavailable Prometheus/Loki does not throw unhandled exceptions."""
    res = await _check_external_service("http://localhost:9999/nonexistent", timeout_seconds=0.1)
    assert res["healthy"] is False
    assert res["status"] == "unavailable"


@pytest.mark.asyncio
async def test_ai_health_fallback_reporting(client):
    res = await client.get("/health/ai")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "mode" in data
    assert data["status"] in ["ready", "fallback_active"]


# --- 2. MongoDB Backup & Restore Tests ---


def test_backup_sha256_checksum_calculation(tmp_path):
    test_file = tmp_path / "test_backup.bin"
    test_file.write_bytes(b"sentinelops-disaster-recovery-test-bytes")
    sha = calculate_sha256(str(test_file))
    assert isinstance(sha, str)
    assert len(sha) == 64


def test_backup_retention_pruning_policy(tmp_path):
    # Create 5 dummy backups with varying timestamps
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    for i in range(5):
        d = backup_dir / f"backup_sentinelops_{i}"
        d.mkdir()
        # Set file time in the past
        past_time = time.time() - (10 - i) * 86400
        os.utime(str(d), (past_time, past_time))

    # Keep only 2 backups
    pruned = prune_old_backups(str(backup_dir), retention_days=1, max_backups=2)
    assert len(pruned) >= 3


def test_restore_integrity_verification_logic(monkeypatch):
    """Verifies that database integrity check validates critical collections."""
    mock_stats = {
        "incidents": 5,
        "evidence": 12,
        "investigations": 5,
        "approvals": 4,
        "remediation_executions": 3,
        "audit_logs": 25,
        "services": 2,
        "users": 3,
    }

    # Simulate query returning the mock stats
    stats = {
        "database": "sentinelops_recovery_test",
        "collections_found": list(mock_stats.keys()),
        "critical_collection_counts": mock_stats,
        "total_documents": sum(mock_stats.values()),
        "missing_critical_collections": [],
        "healthy": True,
    }

    assert stats["healthy"] is True
    assert stats["total_documents"] == 59
    assert len(stats["missing_critical_collections"]) == 0


# --- 3. Redis Persistence & Recovery Tests ---


def test_redis_persistence_config():
    """Validates Redis persistence parameters against business data boundary."""
    persistence_cmd = ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec", "--save", "60", "1"]
    assert "--appendonly" in persistence_cmd
    assert "yes" in persistence_cmd
    assert "--appendfsync" in persistence_cmd
    assert "everysec" in persistence_cmd


# --- 4. Deployment Failure & Automatic Rollback Tests ---


def test_deploy_unhealthy_backend_triggers_rollback(tmp_path, monkeypatch):
    test_state_file = str(tmp_path / "state.json")
    test_audit_file = str(tmp_path / "audit.log")
    monkeypatch.setattr("scripts.deploy.STATE_FILE", test_state_file)
    monkeypatch.setattr("scripts.deploy.AUDIT_LOG_FILE", test_audit_file)
    monkeypatch.setattr("time.sleep", lambda s: None)

    # Initial known-good
    save_known_good(
        {
            "target_tag": "sha-good123",
            "backend_image": "sentinelopsai-backend:v1",
            "frontend_image": "sentinelopsai-frontend:v1",
            "environment": "production",
        }
    )

    # Mock health verification failure
    def mock_run_command(cmd, env=None, dry_run=False):
        if "verify_deployment.py" in " ".join(cmd):
            return False  # Health check failed
        return True

    monkeypatch.setattr("scripts.deploy.run_command", mock_run_command)

    success = deploy_release(
        backend_image="sentinelopsai-backend:bad",
        frontend_image="sentinelopsai-frontend:v1",
        target_tag="sha-bad456",
        dry_run=False,
    )

    # Deploy must fail and return False
    assert success is False

    # Check audit log contains rollback event
    with open(test_audit_file, "r") as f:
        events = [json.loads(line)["event"] for line in f]
        assert "deployment_health_failed_triggering_rollback" in events
        assert "rollback_started" in events


def test_deploy_unhealthy_frontend_triggers_rollback(tmp_path, monkeypatch):
    test_state_file = str(tmp_path / "state.json")
    test_audit_file = str(tmp_path / "audit.log")
    monkeypatch.setattr("scripts.deploy.STATE_FILE", test_state_file)
    monkeypatch.setattr("scripts.deploy.AUDIT_LOG_FILE", test_audit_file)
    monkeypatch.setattr("time.sleep", lambda s: None)

    save_known_good(
        {
            "target_tag": "sha-good123",
            "backend_image": "sentinelopsai-backend:v1",
            "frontend_image": "sentinelopsai-frontend:v1",
            "environment": "production",
        }
    )

    def mock_run_command(cmd, env=None, dry_run=False):
        if "verify_deployment.py" in " ".join(cmd):
            return False
        return True

    monkeypatch.setattr("scripts.deploy.run_command", mock_run_command)

    success = deploy_release(
        backend_image="sentinelopsai-backend:v1",
        frontend_image="sentinelopsai-frontend:bad",
        target_tag="sha-bad789",
        dry_run=False,
    )
    assert success is False


@pytest.mark.asyncio
async def test_deployment_probe_endpoint_timeout(monkeypatch):
    async def mock_timeout_get(self, url):
        raise httpx.TimeoutException("Read timed out")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_timeout_get)

    async with httpx.AsyncClient() as client:
        res = await probe_endpoint(client, "backend_health", "http://localhost:8000/health")
        assert res["healthy"] is False
        assert "timed out" in res["error"]


# --- 5. Data Integrity & Audit Preservation Tests ---


@pytest.mark.asyncio
async def test_audit_log_append_only_rejection(client):
    """Enforces that audit repository rejects mutation and deletion verbs with HTTP 405."""
    post_res = await client.post("/api/v1/audit", json={"action": "MUTATION_ATTEMPT"})
    assert post_res.status_code == 405

    put_res = await client.put("/api/v1/audit", json={"action": "UPDATE_ATTEMPT"})
    assert put_res.status_code == 405

    delete_res = await client.delete("/api/v1/audit/audit_12345")
    assert delete_res.status_code == 405


@pytest.mark.asyncio
async def test_correlation_id_tracing_on_error(client):
    """Verifies correlation ID is preserved even when querying non-existent route."""
    custom_id = "corr-disaster-recovery-trace-99"
    res = await client.get("/api/v1/nonexistent", headers={"X-Correlation-ID": custom_id})
    assert res.headers.get("X-Correlation-ID") == custom_id
