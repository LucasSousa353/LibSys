from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics.repository import AnalyticsRepository
from app.domains.analytics.schemas import (
    DashboardSummary,
    MostBorrowedBookItem,
)


class AnalyticsService:
    """Serviço analítico unificado para Dashboard."""

    def __init__(self, db: AsyncSession):
        self.repository = AnalyticsRepository(db)

    async def get_dashboard_summary(self) -> DashboardSummary:
        """Retorna todos os indicadores do dashboard unificado."""
        now = datetime.now(timezone.utc)

        total_books = await self.repository.count_total_books()
        total_users = await self.repository.count_total_users()
        active_loans = await self.repository.count_active_loans()
        overdue_loans = await self.repository.count_overdue_loans(now)
        total_fines = await self.repository.sum_total_fines()
        recent_books_models = await self.repository.find_recent_books(limit=5)
        most_borrowed_rows = await self.repository.find_most_borrowed_books(limit=5)

        recent_books = [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "isbn": b.isbn,
                "total_copies": b.total_copies,
                "available_copies": b.available_copies,
            }
            for b in recent_books_models
        ]

        most_borrowed_books = [
            MostBorrowedBookItem(
                book_id=row[0],
                title=row[1],
                author=row[2],
                loan_count=row[3],
            )
            for row in most_borrowed_rows
        ]

        return DashboardSummary(
            total_books=total_books,
            total_users=total_users,
            active_loans=active_loans,
            overdue_loans=overdue_loans,
            total_fines=total_fines,
            recent_books=recent_books,
            most_borrowed_books=most_borrowed_books,
        )
