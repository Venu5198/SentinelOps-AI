import pytest


@pytest.mark.asyncio
async def test_user_registration_and_login(client):
    reg_payload = {"email": "testops@sentinelops.com", "password": "Password123!", "role": "operator"}
    # Register
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == reg_payload["email"]
    assert data["role"] == "operator"

    # Login
    login_res = await client.post(
        "/api/v1/auth/login", json={"email": reg_payload["email"], "password": reg_payload["password"]}
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Verify Profile
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == reg_payload["email"]


@pytest.mark.asyncio
async def test_rbac_protection_viewer_forbidden_from_admin_actions(client, viewer_token):
    # Viewer tries to register a service (admin-only)
    svc_payload = {"name": "unauthorized-service", "environment": "local", "endpoint_url": "http://localhost:9999"}
    res = await client.post("/api/v1/services", json=svc_payload, headers={"Authorization": f"Bearer {viewer_token}"})
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"]


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client):
    res = await client.get("/api/v1/incidents")
    assert res.status_code == 401
