import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["project"] == "SentinelOps AI"
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_ready_endpoint(client):
    res = await client.get("/ready")
    assert res.status_code in [200, 503]
    data = res.json()
    assert "components" in data
    assert "mongodb" in data["components"]
    assert "redis" in data["components"]


@pytest.mark.asyncio
async def test_correlation_id_middleware(client):
    custom_id = "test-corr-id-12345"
    res = await client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("X-Correlation-ID") == custom_id

