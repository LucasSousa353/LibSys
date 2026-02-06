from typing import Annotated
from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import get_db
from app.domains.auth.dependencies import require_roles
from app.domains.users.models import User
from app.domains.users.schemas import UserRole
from app.domains.notifications.schemas import (
    NotificationDispatchRequest,
    NotificationDispatchResponse,
)
from app.domains.notifications.services import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(
    db: AsyncSession = Depends(get_db),
) -> NotificationService:
    return NotificationService(db)


@router.post("/dispatch", response_model=NotificationDispatchResponse)
async def dispatch_notifications(
    current_user: Annotated[
        User, Depends(require_roles({UserRole.ADMIN.value, UserRole.LIBRARIAN.value}))
    ],
    payload: NotificationDispatchRequest = Body(
        default_factory=NotificationDispatchRequest
    ),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.dispatch_due_notifications(
        channels=payload.channels, limit=payload.limit
    )
