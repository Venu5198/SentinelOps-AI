import pytest


@pytest.mark.asyncio
async def test_full_incident_investigation_approval_and_remediation_flow(
    client, operator_token, viewer_token
):
    # 1. Ingest alert to trigger incident
    alert_payload = {
        "status": "firing",
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "PaymentGatewayTimeout",
                "service": "payment-service",
                "severity": "high"
            },
            "annotations": {
                "summary": "Payment Service 504 Gateway Timeout spike",
                "description": "Repeated connection pool timeouts"
            },
            "fingerprint": "fp_flow_test_1001"
        }]
    }
    ingest_res = await client.post("/api/v1/alerts/webhook", json=alert_payload)
    assert ingest_res.status_code == 200
    incident_id = ingest_res.json()["results"][0]["incident_id"]

    # 2. Trigger AI Investigation (FR-05, AC-07)
    inv_res = await client.post(
        f"/api/v1/incidents/{incident_id}/investigations",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert inv_res.status_code == 201
    inv_data = inv_res.json()
    assert inv_data["status"] == "completed"
    report = inv_data["report"]
    assert report["affected_service"] == "payment-service"
    assert len(report["probable_root_causes"]) >= 1
    assert report["confidence_score"] > 0
    assert len(report["recommended_actions"]) >= 1
    action = report["recommended_actions"][0]
    assert action["action_id"] == "service.restart_container"

    # Verify incident state progressed to AWAITING_APPROVAL
    inc_check = await client.get(
        f"/api/v1/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert inc_check.json()["status"] == "AWAITING_APPROVAL"

    # 3. List Approvals
    appr_list_res = await client.get(
        f"/api/v1/approvals?incident_id={incident_id}",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert appr_list_res.status_code == 200
    approvals = appr_list_res.json()
    assert len(approvals) >= 1
    approval_id = approvals[0]["id"]
    assert approvals[0]["status"] == "PENDING"

    # 4. Viewer tries to approve -> FORBIDDEN (AC-09)
    forbidden_res = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "APPROVED", "reason": "Viewer trying unauthorized approval"},
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert forbidden_res.status_code == 403

    # 5. Operator approves -> SUCCESS (AC-11)
    approve_res = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "APPROVED", "reason": "Operator verified logs and approved restart"},
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 6. Execute Approved Allowlisted Action (FR-08, AC-11, AC-12)
    exec_res = await client.post(
        "/api/v1/remediations/execute",
        json={"incident_id": incident_id, "approval_id": approval_id},
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert exec_res.status_code == 201
    exec_data = exec_res.json()
    assert exec_data["status"] == "COMPLETED"
    assert exec_data["action_id"] == "service.restart_container"

    # 7. Check Audit Logs (FR-11, AC-16)
    audit_res = await client.get(
        f"/api/v1/audit?resource_id={incident_id}",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1

    # 8. Generate Final Post-Incident Report (FR-12, AC-18)
    rep_res = await client.get(
        f"/api/v1/reports/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert "markdown_report" in rep_data
    assert "Post-Mortem Report" in rep_data["markdown_report"]

