from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import get_db
from app.domains.auth.dependencies import require_roles
from app.domains.users.models import User
from app.domains.users.schemas import UserRole
from app.domains.analytics.schemas import DashboardSummary
from app.domains.analytics.services import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    current_user: Annotated[
        User, Depends(require_roles({UserRole.ADMIN.value}))
    ],
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Retorna indicadores unificados do dashboard (admin only)."""
    return await service.get_dashboard_summary()
