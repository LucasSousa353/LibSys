from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import List, Optional, Callable

from app.domains.loans.models import Loan, LoanStatus
from app.domains.loans.schemas import LoanCreate
from app.domains.loans.repository import LoanRepository
from app.domains.books.repository import BookRepository
from app.domains.users.repository import UserRepository
from app.core.config import settings
from app.core.messages import ErrorMessages, SuccessMessages


def get_now() -> datetime:
    return datetime.now(timezone.utc)


class LoanService:
    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        get_now_fn: Callable[[], datetime] = get_now,
    ):
        self.db = db
        self.redis = redis
        self.get_now = get_now_fn
        self.loan_repository = LoanRepository(db)
        self.book_repository = BookRepository(db)
        self.user_repository = UserRepository(db)

    async def create_loan(self, loan_in: LoanCreate) -> Loan:
        """
        Cria um novo empréstimo no sistema com validações de negócio.

        Validações realizadas:
        - Livro existe e está disponível
        - Usuário existe
        - Usuário não atingiu limite de empréstimos ativos
        - Usuário não possui empréstimos atrasados

        Args:
            loan_in: Dados do empréstimo a ser criado

        Returns:
            Loan: Empréstimo criado

        Raises:
            LookupError: Se livro ou usuário não for encontrado
            ValueError: Se livro não disponível, limite atingido ou usuário com atrasos
        """
        # 1. Buscar Livro com LOCK PESSIMISTA
        book = await self.book_repository.find_by_id_with_lock(loan_in.book_id)

        if not book:
            raise LookupError(ErrorMessages.BOOK_NOT_FOUND)

        if book.available_copies < 1:
            raise ValueError(ErrorMessages.BOOK_NOT_AVAILABLE)

        # 2. Verificar usuário
        user = await self.user_repository.find_by_id(loan_in.user_id)
        if not user:
            raise LookupError(ErrorMessages.USER_NOT_FOUND)

        # 3. Verificar limite
        active_count = await self.loan_repository.count_active_loans_by_user(
            loan_in.user_id
        )

        if active_count >= settings.MAX_ACTIVE_LOANS:
            raise ValueError(
                ErrorMessages.LOAN_MAX_ACTIVE_LIMIT.format(
                    limit=settings.MAX_ACTIVE_LOANS
                )
            )

        # 4. Verificar atrasos (Bloqueio)
        now = self.get_now()
        overdue_loan = await self.loan_repository.find_overdue_loans_by_user(
            loan_in.user_id, now
        )
        if overdue_loan:
            raise ValueError(ErrorMessages.LOAN_USER_HAS_OVERDUE)

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
        await self.book_repository.update(book)
        new_loan = await self.loan_repository.create(new_loan)

        # 6. Invalidar Cache
        await self._invalidate_books_cache()

        return new_loan

    async def return_loan(self, loan_id: int, current_user_id: int) -> dict:
        """
        Processa a devolução de um empréstimo com cálculo de multa.

        Calcula multa por dias de atraso se aplicável e atualiza o estoque.

        Args:
            loan_id: ID do empréstimo a ser devolvido
            current_user_id: ID do usuário que está devolvendo

        Returns:
            dict: Informações sobre a devolução (mensagem, ID, multa, dias de atraso)

        Raises:
            LookupError: Se empréstimo não for encontrado
            PermissionError: Se usuário tentar devolver empréstimo de outro usuário
            ValueError: Se empréstimo já foi devolvido
        """
        # Lock no Empréstimo
        loan = await self.loan_repository.find_by_id_with_lock(loan_id)

        if not loan:
            raise LookupError(ErrorMessages.LOAN_NOT_FOUND)

        # Validar que o empréstimo pertence ao usuário
        if loan.user_id != current_user_id:
            raise PermissionError(ErrorMessages.LOAN_PERMISSION_DENIED)

        if loan.status == LoanStatus.RETURNED:
            raise ValueError(ErrorMessages.LOAN_ALREADY_RETURNED)

        # Lock no Livro
        book = await self.book_repository.find_by_id_with_lock(loan.book_id)

        # Cálculos
        now = self.get_now()
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
            await self.book_repository.update(book)

        await self.loan_repository.update(loan)
        await self._invalidate_books_cache()

        return {
            "message": SuccessMessages.LOAN_RETURNED,
            "loan_id": loan.id,
            "fine_amount": f"R$ {fine:.2f}",
            "days_overdue": max(0, days_overdue),
        }

    async def _invalidate_books_cache(self):
        """Helper privado para limpar cache de listagem de livros."""
        async for key in self.redis.scan_iter("books:list:*"):
            await self.redis.delete(key)

    async def list_loans(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> List[Loan]:
        """
        Lista empréstimos com filtros opcionais e paginação.

        Atualiza automaticamente status para OVERDUE quando aplicável.

        Args:
            user_id: Filtro opcional por ID do usuário
            status: Filtro opcional por status (ACTIVE, RETURNED, OVERDUE)
            skip: Número de registros a pular (paginação)
            limit: Número máximo de registros a retornar

        Returns:
            List[Loan]: Lista de empréstimos
        """
        now = self.get_now()

        # Para filtro OVERDUE, buscar loans ACTIVE com data vencida
        if status == LoanStatus.OVERDUE:
            loans = await self.loan_repository.find_all(
                user_id=user_id, status=LoanStatus.ACTIVE, skip=skip, limit=limit
            )
            # Filtrar apenas os vencidos
            overdue_loans = [
                loan
                for loan in loans
                if loan.expected_return_date.replace(tzinfo=timezone.utc) < now
            ]
            # Atualizar status temporariamente (não persiste)
            for loan in overdue_loans:
                loan.status = LoanStatus.OVERDUE
            return overdue_loans  # type: ignore

        # Para outros status, buscar diretamente
        loans = await self.loan_repository.find_all(
            user_id=user_id, status=status, skip=skip, limit=limit
        )

        # Atualizar status ACTIVE para OVERDUE se necessário
        for loan in loans:
            expected = loan.expected_return_date
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=timezone.utc)

            if loan.status == LoanStatus.ACTIVE and expected < now:
                loan.status = LoanStatus.OVERDUE

        return loans  # type: ignore
