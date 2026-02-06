from typing import Protocol
import structlog

from app.domains.notifications.models import Notification

logger = structlog.get_logger()


class Notifier(Protocol):
    async def send(self, notification: Notification) -> None: ...


class EmailNotifier:
    async def send(self, notification: Notification) -> None:
        logger.info(
            "notification_email_sent",
            notification_id=notification.id,
            user_id=notification.user_id,
            loan_id=notification.loan_id,
            subject=notification.subject,
        )


class WebhookNotifier:
    async def send(self, notification: Notification) -> None:
        logger.info(
            "notification_webhook_sent",
            notification_id=notification.id,
            user_id=notification.user_id,
            loan_id=notification.loan_id,
            subject=notification.subject,
        )
