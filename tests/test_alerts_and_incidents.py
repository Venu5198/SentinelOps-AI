import pytest


@pytest.mark.asyncio
async def test_alertmanager_webhook_and_deduplication(client, operator_token):
    # Alertmanager payload with high error rate alert
    webhook_payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "PaymentHighErrorRate", "service": "payment-service", "severity": "critical"},
                "annotations": {
                    "summary": "Payment Service HTTP 500 error spike",
                    "description": "500 Internal Server Error rate exceeds 5%",
                },
                "fingerprint": "fp_payment_500_test",
            }
        ],
    }

    # 1. Ingest alert -> Creates incident
    res = await client.post("/api/v1/alerts/webhook", json=webhook_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["processed_count"] == 1
    assert data["results"][0]["was_created_new"] is True
    inc_id = data["results"][0]["incident_id"]

    # 2. Ingest duplicate alert with same fingerprint -> Updates existing incident (AC-03)
    res_dup = await client.post("/api/v1/alerts/webhook", json=webhook_payload)
    assert res_dup.status_code == 200
    dup_data = res_dup.json()
    assert dup_data["results"][0]["was_created_new"] is False
    assert dup_data["results"][0]["incident_id"] == inc_id
    assert dup_data["results"][0]["occurrence_count"] >= 2

    # 3. Retrieve incident
    inc_res = await client.get(f"/api/v1/incidents/{inc_id}", headers={"Authorization": f"Bearer {operator_token}"})
    assert inc_res.status_code == 200
    assert inc_res.json()["status"] == "DETECTED"


@pytest.mark.asyncio
async def test_invalid_lifecycle_transition_rejected(client, operator_token):
    # Create an alert to have an incident in DETECTED status
    res = await client.post(
        "/api/v1/alerts/webhook",
        json={
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "TestAlert", "service": "order-service", "severity": "medium"},
                    "annotations": {"summary": "Test"},
                    "fingerprint": "fp_test_transition",
                }
            ],
        },
    )
    inc_id = res.json()["results"][0]["incident_id"]

    # Attempt illegal jump: DETECTED -> RESOLVED directly without investigation/verification
    bad_trans = await client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert bad_trans.status_code == 400
    assert "Invalid state transition" in bad_trans.json()["detail"]


@pytest.mark.asyncio
async def test_malformed_alert_rejected(client):
    # Alert missing mandatory alertname
    bad_payload = {"status": "firing", "alerts": [{"status": "firing", "labels": {"service": "broken-alert"}}]}
    res = await client.post("/api/v1/alerts/webhook", json=bad_payload)
    assert res.status_code == 422
