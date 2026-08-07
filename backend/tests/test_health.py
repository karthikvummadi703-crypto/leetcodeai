"""
Tests for the /api/health endpoint.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_contains_environment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    data = response.json()
    assert "environment" in data
