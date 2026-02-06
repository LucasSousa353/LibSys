import pytest
from httpx import AsyncClient


class TestAnalyticsDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, client_unauthenticated: AsyncClient):
        response = await client_unauthenticated.get("/analytics/dashboard")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dashboard_requires_admin(self, client_user: AsyncClient):
        response = await client_user.get("/analytics/dashboard")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_dashboard_returns_summary(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        book = await create_book()
        await create_loan(user_id=authenticated_user.id, book_id=book.id)

        response = await client.get("/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert "total_books" in data
        assert "total_users" in data
        assert "active_loans" in data
        assert "overdue_loans" in data
        assert "total_fines" in data
        assert "recent_books" in data
        assert "most_borrowed_books" in data
        assert data["total_books"] >= 1
        assert data["total_users"] >= 1
        assert data["active_loans"] >= 1
