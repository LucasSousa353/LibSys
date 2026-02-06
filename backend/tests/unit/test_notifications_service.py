from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.loans.models import Loan, LoanStatus
from app.domains.notifications.models import NotificationChannel
from app.domains.notifications.services import NotificationService
from app.domains.users.models import User
from app.domains.books.models import Book


class TestNotificationServiceFixtures:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        service = NotificationService(db=mock_db)
        service.loan_repository = MagicMock()
        service.notification_repository = MagicMock()
        service.notification_repository.exists_for_loan = AsyncMock(return_value=False)
        service.notification_repository.create = AsyncMock()
        service.notifiers = {
            NotificationChannel.EMAIL.value: MagicMock(send=AsyncMock()),
            NotificationChannel.WEBHOOK.value: MagicMock(send=AsyncMock()),
        }
        return service

    @pytest.fixture
    def sample_loan(self):
        now = datetime.now(timezone.utc)
        user = User(
            id=1, name="Test User", email="test@example.com", hashed_password="hash"
        )
        book = Book(
            id=1,
            title="Test Book",
            author="Author",
            isbn="ISBN-001",
            total_copies=1,
            available_copies=1,
        )
        loan = Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=now - timedelta(days=5),
            expected_return_date=now + timedelta(days=1),
            status=LoanStatus.ACTIVE,
            fine_amount=0,
        )
        loan.user = user
        loan.book = book
        return loan


class TestNotificationService(TestNotificationServiceFixtures):
    def test_normalize_channels_default(self, service):
        channels = service._normalize_channels(None)
        assert NotificationChannel.EMAIL.value in channels
        assert NotificationChannel.WEBHOOK.value in channels

    def test_normalize_channels_filters_invalid(self, service):
        channels = service._normalize_channels(["email", "invalid", "webhook"])
        assert channels == ["email", "webhook"]

    @pytest.mark.asyncio
    async def test_dispatch_due_notifications_counts(self, service, sample_loan):
        service.loan_repository.find_due_soon_with_relations = AsyncMock(
            return_value=[sample_loan]
        )
        service.loan_repository.find_overdue_with_relations = AsyncMock(
            return_value=[sample_loan]
        )

        result = await service.dispatch_due_notifications(channels=["email"])

        assert result["due_soon_sent"] == 1
        assert result["overdue_sent"] == 1
        assert result["total_sent"] == 2
