import pytest
from httpx import AsyncClient


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["postgres"] == "ok"
        assert data["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_health_check_returns_all_components(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "postgres" in data
        assert "redis" in data

    @pytest.mark.asyncio
    async def test_health_check_does_not_require_authentication(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get("/health")
        assert response.status_code == 200
