import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint returns ok."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_health_returns_database_status(client):
    """Test health check includes database status."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
