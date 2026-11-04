import json
import os
import pytest
from scripts.deploy import (
    load_known_good,
    save_known_good,
    deploy_release,
    rollback_release,
    STATE_FILE,
    AUDIT_LOG_FILE,
)
from scripts.verify_deployment import probe_endpoint, verify_deployment
import httpx


@pytest.mark.asyncio
async def test_deployment_probe_endpoint_healthy(monkeypatch):
    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "components": {
                    "mongodb": "connected",
                    "redis": "connected"
                }
            }

    async def mock_get(self, url):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    async with httpx.AsyncClient() as client:
        res = await probe_endpoint(client, "backend_ready", "http://localhost:8000/ready")
        assert res["healthy"] is True
        assert res["status_code"] == 200
        assert res["details"]["mongodb"] == "connected"


@pytest.mark.asyncio
async def test_deployment_probe_endpoint_unhealthy_component(monkeypatch):
    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "components": {
                    "mongodb": "unhealthy",
                    "redis": "connected"
                }
            }

    async def mock_get(self, url):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    async with httpx.AsyncClient() as client:
        res = await probe_endpoint(client, "backend_ready", "http://localhost:8000/ready")
        assert res["healthy"] is False


@pytest.mark.asyncio
async def test_verify_deployment_healthy_streak(monkeypatch):
    class MockResponse:
        status_code = 200
        def json(self):
            return {"components": {"mongodb": "connected", "redis": "connected"}}

    async def mock_get(self, url):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    success = await verify_deployment(
        target_sha="d77891d",
        consecutive_probes=2,
        probe_interval_seconds=0.01,
        max_retries=3,
        custom_targets={"test_svc": "http://localhost:8000/health"}
    )
    assert success is True


def test_deploy_controller_state_save_and_load(tmp_path, monkeypatch):
    test_state_file = str(tmp_path / "test_state.json")
    monkeypatch.setattr("scripts.deploy.STATE_FILE", test_state_file)

    state = {
        "target_tag": "sha-abc1234",
        "backend_image": "ghcr.io/test/backend:sha-abc1234",
        "frontend_image": "ghcr.io/test/frontend:sha-abc1234",
        "environment": "staging"
    }
    save_known_good(state)
    loaded = load_known_good()
    assert loaded is not None
    assert loaded["target_tag"] == "sha-abc1234"
    assert loaded["backend_image"] == "ghcr.io/test/backend:sha-abc1234"


def test_deploy_release_dry_run(tmp_path, monkeypatch):
    test_state_file = str(tmp_path / "test_state.json")
    test_audit_file = str(tmp_path / "test_audit.log")
    monkeypatch.setattr("scripts.deploy.STATE_FILE", test_state_file)
    monkeypatch.setattr("scripts.deploy.AUDIT_LOG_FILE", test_audit_file)

    # In dry-run mode, deploy should succeed without invoking real docker
    success = deploy_release(
        backend_image="ghcr.io/org/backend:d77891d",
        frontend_image="ghcr.io/org/frontend:d77891d",
        target_tag="d77891d",
        environment="staging",
        dry_run=True
    )
    assert success is True

    # Confirm audit log was generated
    assert os.path.exists(test_audit_file)
    with open(test_audit_file, "r") as f:
        lines = f.readlines()
        assert len(lines) >= 1
        record = json.loads(lines[0])
        assert record["event"] == "deployment_started"


def test_rollback_release_dry_run(tmp_path, monkeypatch):
    test_state_file = str(tmp_path / "test_state.json")
    test_audit_file = str(tmp_path / "test_audit.log")
    monkeypatch.setattr("scripts.deploy.STATE_FILE", test_state_file)
    monkeypatch.setattr("scripts.deploy.AUDIT_LOG_FILE", test_audit_file)

    # Seed known-good state
    save_known_good({
        "target_tag": "v1.0.0-stable",
        "backend_image": "ghcr.io/org/backend:v1.0.0-stable",
        "frontend_image": "ghcr.io/org/frontend:v1.0.0-stable",
        "environment": "production"
    })

    # Trigger rollback
    success = rollback_release(target_tag="v1.0.0-stable", dry_run=True)
    assert success is True

    # Verify rollback event logged
    with open(test_audit_file, "r") as f:
        events = [json.loads(line)["event"] for line in f]
        assert "rollback_started" in events
