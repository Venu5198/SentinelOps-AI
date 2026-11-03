from datetime import datetime, timedelta, timezone

import pytest

from backend.db.mongodb import get_database
from backend.db.redis import acquire_distributed_lock, release_distributed_lock
from backend.services.approval_service import compute_action_signature, verify_action_signature


@pytest.mark.asyncio
async def test_keyed_hmac_signature_verification():
    # 1. Correct signature validates
    sig = compute_action_signature("service.restart_container", "payment-service", {"foo": "bar"})
    assert verify_action_signature(sig, "service.restart_container", "payment-service", {"foo": "bar"}) is True

    # 2. Tampered parameters fail
    assert verify_action_signature(sig, "service.restart_container", "payment-service", {"foo": "tampered"}) is False

    # 3. Tampered service fails
    assert verify_action_signature(sig, "service.restart_container", "order-service", {"foo": "bar"}) is False

    # 4. Tampered action fails
    assert verify_action_signature(sig, "service.stop_container", "payment-service", {"foo": "bar"}) is False

    # 5. Wrong secret key fails
    wrong_sig = compute_action_signature(
        "service.restart_container", "payment-service", {"foo": "bar"}, secret_key="wrong_key"
    )
    assert verify_action_signature(wrong_sig, "service.restart_container", "payment-service", {"foo": "bar"}) is False


@pytest.mark.asyncio
async def test_audit_log_append_only_mutation_rejected(client, operator_token):
    headers = {"Authorization": f"Bearer {operator_token}"}

    # POST to /audit is rejected with 405
    res = await client.post("/api/v1/audit", json={"action": "HACK"}, headers=headers)
    assert res.status_code == 405

    # DELETE to /audit is rejected with 405
    res = await client.delete("/api/v1/audit", headers=headers)
    assert res.status_code == 405

    # DELETE /audit/{id} is rejected with 405
    res = await client.delete("/api/v1/audit/audit_123", headers=headers)
    assert res.status_code == 405


@pytest.mark.asyncio
async def test_redis_distributed_lock_unique_token_and_release():
    key = "test_target_service_mutex"

    # 1. First worker acquires lock
    token1 = await acquire_distributed_lock(key, timeout_seconds=5)
    assert token1 is not None

    # 2. Second worker cannot acquire same lock
    token2 = await acquire_distributed_lock(key, timeout_seconds=5)
    assert token2 is None

    # 3. Worker 2 attempts release with wrong token -> does not release
    await release_distributed_lock(key, token="wrong_token_hex")
    assert await acquire_distributed_lock(key, timeout_seconds=5) is None

    # 4. Worker 1 releases with correct token -> lock freed
    await release_distributed_lock(key, token=token1)
    token3 = await acquire_distributed_lock(key, timeout_seconds=5)
    assert token3 is not None
    await release_distributed_lock(key, token=token3)


@pytest.mark.asyncio
async def test_replay_protection_and_tampering_at_execution(client, operator_token):
    db = get_database()
    now = datetime.now(timezone.utc)

    # Seed an approval record
    appr_id = "appr_sec_test_001"
    valid_sig = compute_action_signature("service.restart_container", "payment-service", {})

    await db.approvals.insert_one(
        {
            "_id": appr_id,
            "incident_id": "INC-SEC-001",
            "action_id": "service.restart_container",
            "action_signature": valid_sig,
            "target_service": "payment-service",
            "parameters": {},
            "rationale": "Security replay test",
            "risk_level": "MEDIUM",
            "status": "APPROVED",
            "requested_by": "sentinelops-ai",
            "approved_by": "operator",
            "expires_at": now + timedelta(minutes=10),
            "created_at": now,
        }
    )

    headers = {"Authorization": f"Bearer {operator_token}"}

    # 1. First execution succeeds
    res1 = await client.post(
        "/api/v1/remediations/execute", json={"incident_id": "INC-SEC-001", "approval_id": appr_id}, headers=headers
    )
    assert res1.status_code == 201

    # 2. Replay attack: Second execution with same approval MUST fail with 400 or 409
    res2 = await client.post(
        "/api/v1/remediations/execute", json={"incident_id": "INC-SEC-001", "approval_id": appr_id}, headers=headers
    )
    assert res2.status_code in [400, 409]


@pytest.mark.asyncio
async def test_expired_approval_rejected_at_execution(client, operator_token):
    db = get_database()
    now = datetime.now(timezone.utc)

    appr_id = "appr_expired_test_001"
    valid_sig = compute_action_signature("service.restart_container", "payment-service", {})

    # Approval created with expiration in the past
    await db.approvals.insert_one(
        {
            "_id": appr_id,
            "incident_id": "INC-SEC-002",
            "action_id": "service.restart_container",
            "action_signature": valid_sig,
            "target_service": "payment-service",
            "parameters": {},
            "rationale": "Expired execution test",
            "risk_level": "MEDIUM",
            "status": "APPROVED",
            "requested_by": "sentinelops-ai",
            "approved_by": "operator",
            "expires_at": now - timedelta(minutes=5),  # already expired
            "created_at": now - timedelta(minutes=20),
        }
    )

    headers = {"Authorization": f"Bearer {operator_token}"}

    res = await client.post(
        "/api/v1/remediations/execute", json={"incident_id": "INC-SEC-002", "approval_id": appr_id}, headers=headers
    )
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()
