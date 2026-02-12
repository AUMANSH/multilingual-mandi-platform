"""
Basic health check tests to verify the testing framework is working.

These tests serve as a foundation to ensure the testing infrastructure
is properly configured before implementing more complex tests.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from mandi_platform.main import app


@pytest.mark.unit
def test_health_endpoint_sync():
    """Test health endpoint using synchronous client."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_endpoint_async(test_client: AsyncClient):
    """Test health endpoint using async client."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_endpoint_detailed(test_client: AsyncClient):
    """Test detailed health endpoint."""
    response = await test_client.get("/health/detailed")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "redis" in data["services"]
    assert "elasticsearch" in data["services"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_with_dependencies(test_client: AsyncClient):
    """Test health endpoint with all dependencies."""
    # Test basic health
    response = await test_client.get("/health")
    assert response.status_code == 200
    
    # Test detailed health
    response = await test_client.get("/health/detailed")
    assert response.status_code == 200
    
    data = response.json()
    
    # All services should be healthy in test environment
    services = data["services"]
    assert services["database"]["status"] == "healthy"
    assert services["redis"]["status"] == "healthy"
    assert services["elasticsearch"]["status"] == "healthy"