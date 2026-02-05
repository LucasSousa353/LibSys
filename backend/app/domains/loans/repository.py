from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.domains.loans.models import Loan, LoanStatus


class LoanRepository:
    """Repository para isolamento de queries de Loans."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, loan_id: int) -> Optional[Loan]:
        """Busca um empréstimo por ID."""
        query = select(Loan).where(Loan.id == loan_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_by_id_with_lock(self, loan_id: int) -> Optional[Loan]:
        """
        Busca um empréstimo por ID com lock pessimista.

        Usado em operações concorrentes como devoluções.
        """
        query = select(Loan).where(Loan.id == loan_id).with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def count_active_loans_by_user(self, user_id: int) -> int:
        """
        Conta empréstimos ativos ou atrasados de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            int: Quantidade de empréstimos ativos
        """
        query = select(func.count(Loan.id)).where(
            Loan.user_id == user_id,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def find_overdue_loans_by_user(
        self, user_id: int, current_date: datetime
    ) -> Optional[Loan]:
        """
        Busca empréstimos atrasados de um usuário.

        Args:
            user_id: ID do usuário
            current_date: Data atual para comparação

        Returns:
            Optional[Loan]: Primeiro empréstimo atrasado encontrado
        """
        query = select(Loan).where(
            Loan.user_id == user_id,
            Loan.status == LoanStatus.ACTIVE,
            Loan.expected_return_date < current_date,
        )
        result = await self.db.execute(query)
        return result.first()  # type: ignore

    async def find_all(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        current_date: Optional[datetime] = None,
    ) -> List[Loan]:
        """
        Lista empréstimos com filtros opcionais e paginação.

        Args:
            user_id: Filtro opcional por ID do usuário
            status: Filtro opcional por status
            skip: Número de registros a pular
            limit: Número máximo de registros a retornar
            current_date: Data atual para comparação (necessário para filtro OVERDUE)

        Returns:
            List[Loan]: Lista de empréstimos encontrados
        """
        query = select(Loan)

        if user_id:
            query = query.where(Loan.user_id == user_id)

        if status:
            if isinstance(status, str):
                try:
                    status_enum = LoanStatus(status.lower())
                except ValueError:
                    return []
            else:
                status_enum = status

            if status_enum == LoanStatus.OVERDUE:
                if current_date is None:
                    current_date = datetime.now(timezone.utc)

                query = query.where(
                    Loan.status == LoanStatus.ACTIVE,
                    Loan.expected_return_date < current_date,
                )
            else:
                query = query.where(Loan.status == status_enum)

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore

    async def find_all_with_relations(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        current_date: Optional[datetime] = None,
    ) -> List[Loan]:
        """
        Lista empréstimos com eager loading de User e Book (evita N+1 problem).

        Use este método quando precisar de User e Book relacionados para evitar
        múltiplas queries ao banco de dados. Tipicamente para exportação/relatorios.

        Args:
            user_id: Filtro opcional por ID do usuário
            status: Filtro opcional por status
            skip: Número de registros a pular
            limit: Número máximo de registros a retornar
            current_date: Data atual para comparação (necessário para filtro OVERDUE)

        Returns:
            List[Loan]: Lista de empréstimos com User e Book já carregados
        """
        query = select(Loan).options(joinedload(Loan.user), joinedload(Loan.book))

        if user_id:
            query = query.where(Loan.user_id == user_id)

        if status:
            if isinstance(status, str):
                try:
                    status_enum = LoanStatus(status.lower())
                except ValueError:
                    return []
            else:
                status_enum = status

            if status_enum == LoanStatus.OVERDUE:
                if current_date is None:
                    current_date = datetime.now(timezone.utc)

                query = query.where(
                    Loan.status == LoanStatus.ACTIVE,
                    Loan.expected_return_date < current_date,
                )
            else:
                query = query.where(Loan.status == status_enum)

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()  # type: ignore

    async def create(self, loan: Loan) -> Loan:
        """Adiciona um novo empréstimo à sessão (sem commit)."""
        self.db.add(loan)
        return loan

    async def update(self, loan: Loan) -> Loan:
        """Atualiza um empréstimo existente (sem commit)."""
        self.db.add(loan)
        return loan
