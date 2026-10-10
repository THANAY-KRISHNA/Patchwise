"""Unit tests for the health endpoint."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_root_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "environment" in data
    assert "database" in data
    assert "llm_provider" in data
    assert "active_plugins" in data


@pytest.mark.asyncio
async def test_health_api_v1_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["llm_provider"] == "none"


@pytest.mark.asyncio
async def test_plugins_overview_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/plugins")
    assert response.status_code == 200
    data = response.json()
    assert "plugins" in data
