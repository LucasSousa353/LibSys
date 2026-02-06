from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.analytics.services import AnalyticsService


class TestAnalyticsService:
    @pytest.mark.asyncio
    async def test_get_dashboard_summary(self):
        service = AnalyticsService(db=MagicMock())
        service.repository = MagicMock()
        service.repository.count_total_books = AsyncMock(return_value=5)
        service.repository.count_total_users = AsyncMock(return_value=3)
        service.repository.count_active_loans = AsyncMock(return_value=2)
        service.repository.count_overdue_loans = AsyncMock(return_value=1)
        service.repository.sum_total_fines = AsyncMock(return_value=Decimal("10.00"))

        recent_book = MagicMock(
            id=1,
            title="Book",
            author="Author",
            isbn="ISBN",
            total_copies=2,
            available_copies=1,
        )
        service.repository.find_recent_books = AsyncMock(return_value=[recent_book])
        service.repository.find_most_borrowed_books = AsyncMock(
            return_value=[(1, "Book", "Author", 7)]
        )

        summary = await service.get_dashboard_summary()

        assert summary.total_books == 5
        assert summary.total_users == 3
        assert summary.active_loans == 2
        assert summary.overdue_loans == 1
        assert summary.total_fines == Decimal("10.00")
        assert summary.recent_books[0]["title"] == "Book"
        assert summary.most_borrowed_books[0].loan_count == 7
