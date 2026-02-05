from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from redis.asyncio import Redis
from typing import List, Optional

from app.domains.loans.models import Loan, LoanStatus
from app.domains.books.models import Book
from app.domains.users.models import User
from app.domains.loans.schemas import LoanCreate
from app.core.config import settings


class LoanService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def create_loan(self, loan_in: LoanCreate) -> Loan:
        # 1. Buscar Livro com LOCK PESSIMISTA
        book_query = select(Book).where(Book.id == loan_in.book_id).with_for_update()
        result = await self.db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            raise LookupError("Livro não encontrado")

        if book.available_copies < 1:
            raise ValueError("Livro não disponível no estoque")

        # 2. Verificar usuário
        user_query = select(User).where(User.id == loan_in.user_id)
        result = await self.db.execute(user_query)
        user = result.scalar_one_or_none()
        if not user:
            raise LookupError("Usuário não localizado")

        # 3. Verificar limite
        active_loans_query = select(func.count(Loan.id)).where(
            Loan.user_id == loan_in.user_id,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
        )
        result = await self.db.execute(active_loans_query)
        active_count = result.scalar() or 0

        if active_count >= settings.MAX_ACTIVE_LOANS:
            raise ValueError(
                f"Usuário atingiu o limite de {settings.MAX_ACTIVE_LOANS} empréstimos ativos"
            )

        # 4. Verificar atrasos (Bloqueio)
        now = datetime.now(timezone.utc)
        overdue_query = select(Loan).where(
            Loan.user_id == loan_in.user_id,
            Loan.status == LoanStatus.ACTIVE,
            Loan.expected_return_date < now,
        )
        result = await self.db.execute(overdue_query)
        if result.first():
            raise ValueError("Usuário possui empréstimos atrasados pendentes")

        # 5. Efetivar Empréstimo
        expected_return = now + timedelta(days=settings.LOAN_DURATION_DAYS)
        new_loan = Loan(
            user_id=loan_in.user_id,
            book_id=loan_in.book_id,
            loan_date=now,
            expected_return_date=expected_return,
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )

        book.available_copies -= 1
        self.db.add(new_loan)
        self.db.add(book)

        await self.db.commit()
        await self.db.refresh(new_loan)

        # 6. Invalidar Cache
        await self._invalidate_books_cache()

        return new_loan

    async def return_loan(self, loan_id: int) -> dict:
        # Lock no Empréstimo
        query = select(Loan).where(Loan.id == loan_id).with_for_update()
        result = await self.db.execute(query)
        loan = result.scalar_one_or_none()

        if not loan:
            raise LookupError("Empréstimo não encontrado")

        if loan.status == LoanStatus.RETURNED:
            raise ValueError("Empréstimo já devolvido")

        # Lock no Livro
        book_query = select(Book).where(Book.id == loan.book_id).with_for_update()
        result = await self.db.execute(book_query)
        book = result.scalar_one_or_none()

        # Cálculos
        now = datetime.now(timezone.utc)
        loan.return_date = now
        loan.status = LoanStatus.RETURNED

        # Cálculo de Multa
        fine = Decimal("0.00")
        expected = loan.expected_return_date
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)

        days_overdue = 0
        if now > expected:
            days_overdue = (now - expected).days
            if days_overdue > 0:
                fine = days_overdue * settings.DAILY_FINE

        # Persistir Multa
        loan.fine_amount = fine

        # Atualizar Estoque
        if book:
            book.available_copies += 1
            self.db.add(book)

        self.db.add(loan)
        await self.db.commit()
        await self.db.refresh(loan)

        await self._invalidate_books_cache()

        return {
            "message": "Livro retornado.",
            "loan_id": loan.id,
            "fine_amount": f"R$ {fine:.2f}",
            "days_overdue": max(0, days_overdue),
        }

    async def _invalidate_books_cache(self):
        """Helper privado para limpar cache de listagem"""
        async for key in self.redis.scan_iter("books:list:*"):
            await self.redis.delete(key)

    async def list_loans(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> List[Loan]:
        query = select(Loan)

        if user_id:
            query = query.where(Loan.user_id == user_id)

        now = datetime.now(timezone.utc)

        if status == LoanStatus.OVERDUE:
            query = query.where(
                Loan.status == LoanStatus.ACTIVE, Loan.expected_return_date < now
            )
        elif status == LoanStatus.ACTIVE:
            query = query.where(Loan.status == LoanStatus.ACTIVE)
        elif status:
            query = query.where(Loan.status == status)

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        loans = result.scalars().all()

        for loan in loans:
            expected = loan.expected_return_date
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=timezone.utc)

            if loan.status == LoanStatus.ACTIVE and expected < now:
                loan.status = LoanStatus.OVERDUE

        return loans  # type: ignore
