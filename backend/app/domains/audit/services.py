from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.models import AuditLog
from app.domains.audit.repository import AuditLogRepository


class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AuditLogRepository(db)

    async def log_event(
        self,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        actor_user_id: int | None = None,
        level: str = "info",
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            level=level,
            message=message,
            metadata_=metadata,
        )
        await self.repository.create(log)
