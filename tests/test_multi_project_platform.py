import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_multi_project_crud_and_isolation(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create Organization
    org_res = await client.post("/api/v1/organizations", json={
        "name": "Acme Enterprise",
        "slug": "acme-enterprise",
        "description": "Multi-tenant test organization"
    }, headers=headers)
    assert org_res.status_code == 201
    org_data = org_res.json()
    org_id = org_data["id"]
    assert org_data["name"] == "Acme Enterprise"

    # 2. Create Project in Org
    proj_res = await client.post("/api/v1/projects", json={
        "name": "Payment Gateway",
        "slug": "payment-gw",
        "description": "Production payment microservices",
        "organization_id": org_id
    }, headers=headers)
    assert proj_res.status_code == 201
    proj_data = proj_res.json()
    proj_id = proj_data["id"]
    assert proj_data["organization_id"] == org_id

    # 3. Verify standard environments were auto-created
    env_res = await client.get(f"/api/v1/projects/{proj_id}/environments", headers=headers)
    assert env_res.status_code == 200
    envs = env_res.json()
    assert len(envs) == 3
    env_slugs = [e["slug"] for e in envs]
    assert "production" in env_slugs

    # 4. Register a service under this project
    svc_res = await client.post("/api/v1/services", json={
        "name": "stripe-connector",
        "project_id": proj_id,
        "environment": "production",
        "service_type": "backend_api",
        "endpoint_url": "http://payment-service:8080",
        "health_endpoint": "/health"
    }, headers=headers)
    assert svc_res.status_code == 201
    svc_data = svc_res.json()
    assert svc_data["project_id"] == proj_id

    # 5. List services scoped by project
    list_res = await client.get(f"/api/v1/services?project_id={proj_id}", headers=headers)
    assert list_res.status_code == 200
    services = list_res.json()
    assert len(services) == 1
    assert services[0]["name"] == "stripe-connector"

    # 6. Global and Project Dashboards
    dash_res = await client.get("/api/v1/dashboard/global", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["summary"]["total_projects"] >= 1

    p_dash = await client.get(f"/api/v1/dashboard/project/{proj_id}", headers=headers)
    assert p_dash.status_code == 200
    p_data = p_dash.json()
    assert p_data["project"]["name"] == "Payment Gateway"
    assert len(p_data["services"]) == 1

    # 7. Create and Test Integration
    integ_res = await client.post("/api/v1/integrations", json={
        "name": "Prometheus Production",
        "integration_type": "prometheus",
        "endpoint_url": "http://prometheus:9090",
        "project_id": proj_id
    }, headers=headers)
    assert integ_res.status_code == 201
    integ_id = integ_res.json()["id"]

    test_res = await client.post(f"/api/v1/integrations/{integ_id}/test", headers=headers)
    assert test_res.status_code == 200
    assert "status" in test_res.json()
