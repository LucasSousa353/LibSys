from pydantic import BaseModel, Field
from app.core.config import settings


class NotificationDispatchRequest(BaseModel):
    channels: list[str] | None = None
    limit: int = Field(
        default=settings.NOTIFICATION_MAX_PER_RUN,
        ge=1,
        le=settings.NOTIFICATION_MAX_PER_RUN,
        description="Máximo de notificações por execução",
    )


class NotificationDispatchResponse(BaseModel):
    due_soon_sent: int
    overdue_sent: int
    total_sent: int
