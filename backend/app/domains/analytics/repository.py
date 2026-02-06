from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.domains.books.models import Book
from app.domains.loans.models import Loan, LoanStatus
from app.domains.users.models import User


class AnalyticsRepository:
    """Repository para queries analíticas isoladas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_total_books(self) -> int:
        query = select(func.count(Book.id))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_total_users(self) -> int:
        query = select(func.count(User.id))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_active_loans(self) -> int:
        query = select(func.count(Loan.id)).where(Loan.status == LoanStatus.ACTIVE)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_overdue_loans(self, current_date: datetime) -> int:
        query = select(func.count(Loan.id)).where(
            Loan.status == LoanStatus.ACTIVE,
            Loan.expected_return_date < current_date,
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def sum_total_fines(self) -> Decimal:
        query = select(func.coalesce(func.sum(Loan.fine_amount), 0))
        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def find_recent_books(self, limit: int = 5) -> List[Book]:
        query = select(Book).order_by(Book.id.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore

    async def find_most_borrowed_books(self, limit: int = 5) -> List[Tuple]:
        """Retorna os livros mais emprestados com contagem."""
        query = (
            select(
                Book.id,
                Book.title,
                Book.author,
                func.count(Loan.id).label("loan_count"),
            )
            .join(Loan, Loan.book_id == Book.id)
            .group_by(Book.id, Book.title, Book.author)
            .order_by(func.count(Loan.id).desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.all()  # type: ignore
