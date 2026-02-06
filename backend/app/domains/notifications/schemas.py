from pydantic import BaseModel


class NotificationDispatchRequest(BaseModel):
    channels: list[str] | None = None
    limit: int | None = None


class NotificationDispatchResponse(BaseModel):
    due_soon_sent: int
    overdue_sent: int
    total_sent: int
