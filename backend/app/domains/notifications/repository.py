from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.domains.notifications.models import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        return notification

    async def exists_for_loan(
        self, loan_id: int, notification_type: str, channel: str
    ) -> bool:
        query = select(func.count(Notification.id)).where(
            Notification.loan_id == loan_id,
            Notification.notification_type == notification_type,
            Notification.channel == channel,
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0
