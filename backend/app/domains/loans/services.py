from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import List, Optional, Callable
import csv
from io import StringIO

from app.domains.loans.models import Loan, LoanStatus
from app.domains.loans.schemas import LoanCreate
from app.domains.loans.repository import LoanRepository
from app.domains.books.repository import BookRepository
from app.domains.users.repository import UserRepository
from app.core.config import settings
from app.core.messages import ErrorMessages, SuccessMessages
from app.core.reports.pdf import PdfTableBuilder


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

        Validações realizadas (SEM lock):
        - Usuário existe
        - Usuário não atingiu limite de empréstimos ativos
        - Usuário não possui empréstimos atrasados

        Validações realizadas (COM lock pessimista):
        - Livro existe e está disponível (lock TARDIO para minimizar contention)

        Ordem de Validação (minimiza Lock Contention Time):
        1. Validar tudo que não precisa de lock (User, Limites, Atrasos) - RÁPIDO
        2. DEPOIS abrir o lock no Livro (recurso mais concorrido)
        3. Verificar estoque do livro e decrementar

        Este padrão reduz drasticamente o tempo que o livro fica bloqueado
        para outros threads que querem alugá-lo.

        Args:
            loan_in: Dados do empréstimo a ser criado

        Returns:
            Loan: Empréstimo criado

        Raises:
            LookupError: Se livro ou usuário não for encontrado
            ValueError: Se livro não disponível, limite atingido ou usuário com atrasos
        """

        # 1. Verificar usuário
        user = await self.user_repository.find_by_id(loan_in.user_id)
        if not user:
            raise LookupError(ErrorMessages.USER_NOT_FOUND)

        # 2. Verificar limite de empréstimos
        active_count = await self.loan_repository.count_active_loans_by_user(
            loan_in.user_id
        )

        if active_count >= settings.MAX_ACTIVE_LOANS:
            raise ValueError(
                ErrorMessages.LOAN_MAX_ACTIVE_LIMIT.format(
                    limit=settings.MAX_ACTIVE_LOANS
                )
            )

        now = self.get_now()
        overdue_loan = await self.loan_repository.find_overdue_loans_by_user(
            loan_in.user_id, now
        )
        if overdue_loan:
            raise ValueError(ErrorMessages.LOAN_USER_HAS_OVERDUE)

        book = await self.book_repository.find_by_id_with_lock(loan_in.book_id)

        if not book:
            raise LookupError(ErrorMessages.BOOK_NOT_FOUND)

        if book.available_copies < 1:
            raise ValueError(ErrorMessages.BOOK_NOT_AVAILABLE)

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

        # Commit da transação (book + loan de forma atômica)
        await self.db.commit()
        await self.db.refresh(new_loan)

        # 6. Invalidar Cache
        await self._invalidate_books_cache()

        return new_loan

    async def return_loan(self, loan_id: int) -> dict:
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

        # Commit da transação (loan + book de forma atômica)
        await self.db.commit()
        await self.db.refresh(loan)

        await self._invalidate_books_cache()

        return {
            "message": SuccessMessages.LOAN_RETURNED,
            "loan_id": loan.id,
            "fine_amount": f"R$ {fine:.2f}",
            "days_overdue": max(0, days_overdue),
        }

    async def extend_loan(self, loan_id: int) -> Loan:
        """Prorroga o prazo de um emprestimo ativo."""
        loan = await self.loan_repository.find_by_id_with_lock(loan_id)

        if not loan:
            raise LookupError(ErrorMessages.LOAN_NOT_FOUND)

        if loan.status == LoanStatus.RETURNED:
            raise ValueError(ErrorMessages.LOAN_ALREADY_RETURNED)

        now = self.get_now()
        expected = loan.expected_return_date
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)

        if loan.status == LoanStatus.OVERDUE or expected < now:
            raise ValueError(ErrorMessages.LOAN_RENEW_OVERDUE)

        if loan.status != LoanStatus.ACTIVE:
            raise ValueError(ErrorMessages.LOAN_RENEW_INVALID_STATUS)

        loan.expected_return_date = expected + timedelta(days=settings.LOAN_DURATION_DAYS)
        await self.loan_repository.update(loan)

        await self.db.commit()
        await self.db.refresh(loan)

        return loan

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

        # Para todos os status (incluindo OVERDUE), buscar diretamente com paginação no banco
        loans = await self.loan_repository.find_all(
            user_id=user_id,
            status=status,
            skip=skip,
            limit=limit,
            current_date=now,
        )

        # Atualizar status ACTIVE para OVERDUE se necessário (para exibição correta)
        for loan in loans:
            expected = loan.expected_return_date
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=timezone.utc)

            if loan.status == LoanStatus.ACTIVE and expected < now:
                loan.status = LoanStatus.OVERDUE

        return loans  # type: ignore

    async def export_loans_csv(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        batch_size: int = 1000,
    ):
        """
        Async Generator que exporta empréstimos em formato CSV com streaming.

        Estratégia de Batching + Eager Loading: Carrega dados em chunks de `batch_size`
        registros usando joinedload para trazer User e Book na mesma query (evita N+1).
        Permite streaming imediato (baixa latência) sem Out-of-Memory.

        Performance:
        - SEM eager loading: 1 query (loans) + N queries (users) + N queries (books) = 2N+1 queries
        - COM eager loading: N/batch_size queries com JOIN (muito mais eficiente)

        Args:
            user_id: Filtro opcional por ID do usuário
            status: Filtro opcional por status
            batch_size: Número de registros a carregar por lote (padrão: 1000)

        Yields:
            str: Chunks do CSV (headers no primeiro chunk, linhas de dados depois)
        """
        # Escrever headers
        fieldnames = [
            "ID",
            "Usuário (ID)",
            "Livro (ID)",
            "Título do Livro",
            "Nome do Usuário",
            "Data do Empréstimo",
            "Data Esperada de Devolução",
            "Data da Devolução",
            "Status",
            "Multa (R$)",
        ]

        # Gerar headers
        headers_output = StringIO()
        headers_writer = csv.DictWriter(headers_output, fieldnames=fieldnames)
        headers_writer.writeheader()
        yield headers_output.getvalue()

        # Processar dados em lotes (batches) COM EAGER LOADING
        now = self.get_now()
        skip = 0

        while True:
            # Buscar um lote de empréstimos COM relações (User e Book já carregados)
            loans = await self.loan_repository.find_all_with_relations(
                user_id=user_id,
                status=status,
                skip=skip,
                limit=batch_size,
                current_date=now,
            )

            # Se não houver mais dados, encerrar
            if not loans:
                break

            # Processar cada lote
            batch_output = StringIO()
            batch_writer = csv.DictWriter(batch_output, fieldnames=fieldnames)

            for loan in loans:
                # Atualizar status OVERDUE se necessário
                expected = loan.expected_return_date
                if expected.tzinfo is None:
                    expected = expected.replace(tzinfo=timezone.utc)

                if loan.status == LoanStatus.ACTIVE and expected < now:
                    loan.status = LoanStatus.OVERDUE

                # Usar relações já carregadas (zero queries adicionais)
                user_name = loan.user.name if loan.user else "N/A"
                book_title = loan.book.title if loan.book else "N/A"

                # Escrever linha no CSV
                batch_writer.writerow(
                    {
                        "ID": loan.id,
                        "Usuário (ID)": loan.user_id,
                        "Livro (ID)": loan.book_id,
                        "Título do Livro": book_title,
                        "Nome do Usuário": user_name,
                        "Data do Empréstimo": loan.loan_date.strftime(
                            "%d/%m/%Y %H:%M:%S"
                        ),
                        "Data Esperada de Devolução": loan.expected_return_date.strftime(
                            "%d/%m/%Y %H:%M:%S"
                        ),
                        "Data da Devolução": (
                            loan.return_date.strftime("%d/%m/%Y %H:%M:%S")
                            if loan.return_date
                            else "Pendente"
                        ),
                        "Status": loan.status.value.upper(),
                        "Multa (R$)": f"{loan.fine_amount:.2f}",
                    }
                )

            # Yield do batch
            yield batch_output.getvalue()

            # Preparar próximo lote
            skip += batch_size

    async def export_loans_pdf_file(
        self,
        file_path: str,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        batch_size: int = 1000,
    ) -> None:
        """Exporta emprestimos em PDF direto para arquivo."""
        headers = [
            "ID",
            "User",
            "Book",
            "Loan Date",
            "Expected Return",
            "Return Date",
            "Status",
            "Fine",
        ]
        pdf = PdfTableBuilder("Loans Export", headers, orientation="L")

        now = self.get_now()
        skip = 0

        while True:
            loans = await self.loan_repository.find_all_with_relations(
                user_id=user_id,
                status=status,
                skip=skip,
                limit=batch_size,
                current_date=now,
            )

            if not loans:
                break

            for loan in loans:
                expected = loan.expected_return_date
                if expected.tzinfo is None:
                    expected = expected.replace(tzinfo=timezone.utc)

                if loan.status == LoanStatus.ACTIVE and expected < now:
                    loan.status = LoanStatus.OVERDUE

                user_name = loan.user.name if loan.user else "N/A"
                book_title = loan.book.title if loan.book else "N/A"
                return_date = (
                    loan.return_date.isoformat() if loan.return_date else "PENDING"
                )

                pdf.add_row(
                    [
                        str(loan.id),
                        f"{user_name} (ID {loan.user_id})",
                        f"{book_title} (ID {loan.book_id})",
                        loan.loan_date.isoformat(),
                        loan.expected_return_date.isoformat(),
                        return_date,
                        loan.status.value,
                        f"{loan.fine_amount:.2f}",
                    ]
                )

            skip += batch_size

        pdf.output_to_file(file_path)
