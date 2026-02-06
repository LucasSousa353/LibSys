from datetime import datetime, timedelta, timezone
from typing import Iterable
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.loans.models import Loan
from app.domains.loans.repository import LoanRepository
from app.domains.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.domains.notifications.repository import NotificationRepository
from app.domains.notifications.providers import EmailNotifier, WebhookNotifier, Notifier

logger = structlog.get_logger()


class NotificationComposer:
    def build_due_soon(self, loan: Loan, now: datetime) -> tuple[str, dict]:
        expected = loan.expected_return_date
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)
        days_left = max(0, (expected - now).days)
        subject = "Loan due soon"
        payload = {
            "type": NotificationType.DUE_SOON.value,
            "user_id": loan.user_id,
            "user_email": getattr(loan.user, "email", None),
            "book_id": loan.book_id,
            "book_title": getattr(loan.book, "title", None),
            "expected_return_date": expected.isoformat(),
            "days_left": days_left,
        }
        return subject, payload

    def build_overdue(self, loan: Loan, now: datetime) -> tuple[str, dict]:
        expected = loan.expected_return_date
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)
        days_overdue = max(0, (now - expected).days)
        subject = "Loan overdue"
        payload = {
            "type": NotificationType.OVERDUE.value,
            "user_id": loan.user_id,
            "user_email": getattr(loan.user, "email", None),
            "book_id": loan.book_id,
            "book_title": getattr(loan.book, "title", None),
            "expected_return_date": expected.isoformat(),
            "days_overdue": days_overdue,
        }
        return subject, payload


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.loan_repository = LoanRepository(db)
        self.notification_repository = NotificationRepository(db)
        self.composer = NotificationComposer()
        self.notifiers: dict[str, Notifier] = {
            NotificationChannel.EMAIL.value: EmailNotifier(),
            NotificationChannel.WEBHOOK.value: WebhookNotifier(),
        }

    async def dispatch_due_notifications(
        self,
        channels: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> dict:
        normalized_channels = self._normalize_channels(channels)
        max_per_run = limit or settings.NOTIFICATION_MAX_PER_RUN
        due_soon_days = settings.NOTIFICATION_DUE_SOON_DAYS

        now = datetime.now(timezone.utc)
        due_soon_end = now + timedelta(days=due_soon_days)

        due_soon_loans = await self.loan_repository.find_due_soon_with_relations(
            now, due_soon_end, max_per_run
        )
        overdue_loans = await self.loan_repository.find_overdue_with_relations(
            now, max_per_run
        )

        due_soon_sent = await self._dispatch_for_loans(
            due_soon_loans, NotificationType.DUE_SOON.value, normalized_channels, now
        )
        overdue_sent = await self._dispatch_for_loans(
            overdue_loans, NotificationType.OVERDUE.value, normalized_channels, now
        )

        await self.db.commit()

        return {
            "due_soon_sent": due_soon_sent,
            "overdue_sent": overdue_sent,
            "total_sent": due_soon_sent + overdue_sent,
        }

    async def _dispatch_for_loans(
        self,
        loans: list[Loan],
        notification_type: str,
        channels: list[str],
        now: datetime,
    ) -> int:
        sent_count = 0
        for loan in loans:
            for channel in channels:
                if await self.notification_repository.exists_for_loan(
                    loan.id, notification_type, channel
                ):
                    continue

                subject, payload = self._compose_payload(notification_type, loan, now)
                notification = Notification(
                    user_id=loan.user_id,
                    loan_id=loan.id,
                    channel=channel,
                    notification_type=notification_type,
                    status=NotificationStatus.PENDING.value,
                    subject=subject,
                    payload=payload,
                )
                await self.notification_repository.create(notification)
                await self.db.flush()

                try:
                    notifier = self.notifiers[channel]
                    await notifier.send(notification)
                    notification.status = NotificationStatus.SENT.value
                    notification.sent_at = datetime.now(timezone.utc)
                    sent_count += 1
                except Exception as exc:
                    logger.error(
                        "notification_send_failed",
                        notification_id=notification.id,
                        error=str(exc),
                        channel=channel,
                    )
                    notification.status = NotificationStatus.FAILED.value
                    notification.error = str(exc)

        return sent_count

    def _compose_payload(
        self, notification_type: str, loan: Loan, now: datetime
    ) -> tuple[str, dict]:
        if notification_type == NotificationType.DUE_SOON.value:
            return self.composer.build_due_soon(loan, now)
        return self.composer.build_overdue(loan, now)

    def _normalize_channels(self, channels: Iterable[str] | None) -> list[str]:
        if not channels:
            return [
                NotificationChannel.EMAIL.value,
                NotificationChannel.WEBHOOK.value,
            ]

        normalized = [str(channel).strip().lower() for channel in channels]
        allowed = set(self.notifiers.keys())
        return [channel for channel in normalized if channel in allowed]
