from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


class TestNotificationsDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_requires_auth(self, client_unauthenticated: AsyncClient):
        response = await client_unauthenticated.post("/notifications/dispatch")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dispatch_requires_staff(self, client_user: AsyncClient):
        response = await client_user.post("/notifications/dispatch")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_dispatch_counts_due_soon_and_overdue(
        self,
        client: AsyncClient,
        authenticated_user,
        create_book,
        create_loan,
    ):
        book = await create_book()
        now = datetime.now(timezone.utc)

        await create_loan(
            user_id=authenticated_user.id,
            book_id=book.id,
            loan_date=now - timedelta(days=1),
            expected_return_date=now + timedelta(days=1),
        )
        await create_loan(
            user_id=authenticated_user.id,
            book_id=book.id,
            loan_date=now - timedelta(days=10),
            expected_return_date=now - timedelta(days=1),
        )

        response = await client.post("/notifications/dispatch")
        assert response.status_code == 200
        data = response.json()
        assert "due_soon_sent" in data
        assert "overdue_sent" in data
        assert data["total_sent"] == data["due_soon_sent"] + data["overdue_sent"]
        assert data["total_sent"] >= 1
