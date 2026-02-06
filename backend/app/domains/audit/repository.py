from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.models import AuditLog


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log: AuditLog) -> None:
        self.db.add(log)
