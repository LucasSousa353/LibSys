import asyncio
import structlog

from app.core.base import SessionLocal
from app.core.config import settings
from app.core.logging.config import configure_logging
from app.domains.notifications.services import NotificationService
from app.domains.users import models as user_models  # noqa: F401
from app.domains.books import models as book_models  # noqa: F401
from app.domains.loans import models as loan_models  # noqa: F401

configure_logging()
logger = structlog.get_logger()


async def dispatch_once() -> dict:
    async with SessionLocal() as db:
        service = NotificationService(db)
        result = await service.dispatch_due_notifications()
        return result


async def scheduler_loop() -> None:
    interval_seconds = settings.NOTIFICATION_SCHEDULER_SECONDS
    logger.info("notifications_scheduler_started", interval_seconds=interval_seconds)
    while True:
        try:
            result = await dispatch_once()
            logger.info("notifications_dispatch_completed", **result)
        except Exception as exc:
            logger.error("notifications_scheduler_failed", error=str(exc))
        await asyncio.sleep(interval_seconds)


def main() -> None:
    asyncio.run(scheduler_loop())


if __name__ == "__main__":
    main()
