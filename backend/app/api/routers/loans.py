from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.base import get_db
from app.models.loan import Loan, LoanStatus
from app.models.book import Book
from app.models.user import User
from app.schemas.loan import LoanCreate, LoanResponse
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/loans", tags=["Loans"])

# Regras de Negócio Constantes. ToDo exportar pra env
MAX_ACTIVE_LOANS = 3
LOAN_DURATION_DAYS = 14
DAILY_FINE = 2.00


@router.post(
    "/",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def create_loan(loan_in: LoanCreate, db: AsyncSession = Depends(get_db)):
    """
    Realiza um empréstimo se todas as regras forem atendidas.
    """

    # 1. Buscar Livro e verificar estoque (Lock Otimista/Simples)
    # ToDo implementar pessimist lock
    book_query = select(Book).where(Book.id == loan_in.book_id)
    book_result = await db.execute(book_query)
    book = book_result.scalar_one_or_none()

    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    if book.available_copies < 1:
        raise HTTPException(status_code=400, detail="Livro não disponível no estoque")

    # 2. Verificar usuário
    user_query = select(User).where(User.id == loan_in.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não localizado")

    # 3. Verificar limite de empréstimos ativos
    active_loans_query = select(func.count(Loan.id)).where(
        Loan.user_id == loan_in.user_id,
        Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
    )
    active_loans_result = await db.execute(active_loans_query)
    active_count = active_loans_result.scalar() or 0

    if active_count >= MAX_ACTIVE_LOANS:
        raise HTTPException(
            status_code=400,
            detail=f"Usuário atingiu o limite de {MAX_ACTIVE_LOANS} empréstimos ativos",
        )

    # 4. [RN05] Verificar se há itens atrasados (Bloqueio)
    # Verifica se existe algum empréstimo ATIVO onde a data esperada é menor que agora
    now = datetime.now(timezone.utc)

    overdue_check_query = select(Loan).where(
        Loan.user_id == loan_in.user_id,
        Loan.status == LoanStatus.ACTIVE,
        Loan.expected_return_date < now,
    )
    overdue_check_result = await db.execute(overdue_check_query)
    if overdue_check_result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário possui empréstimos atrasados pendentes. Regularize antes de novo empréstimo.",
        )

    # 5. Criar Empréstimo e Atualizar Estoque
    expected_return = now + timedelta(days=LOAN_DURATION_DAYS)

    new_loan = Loan(
        user_id=loan_in.user_id,
        book_id=loan_in.book_id,
        loan_date=now,
        expected_return_date=expected_return,
        status=LoanStatus.ACTIVE,
    )

    # Decrementa estoque
    book.available_copies -= 1

    db.add(new_loan)
    db.add(book)

    await db.commit()
    await db.refresh(new_loan)
    return new_loan


@router.post("/{loan_id}/return", status_code=status.HTTP_200_OK)
async def return_loan(loan_id: int, db: AsyncSession = Depends(get_db)):
    """
    Processa a devolução e calcula multa se houver.
    """

    query = select(Loan).where(Loan.id == loan_id)
    result = await db.execute(query)
    loan = result.scalar_one_or_none()

    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status == LoanStatus.RETURNED:
        raise HTTPException(status_code=400, detail="Loan already returned")

    # Lógica de Devolução
    now = datetime.now(timezone.utc)
    loan.return_date = now
    loan.status = LoanStatus.RETURNED

    # Cálculo de Multa
    fine = 0.0
    # Normaliza timezone para garantir comparação correta
    expected = loan.expected_return_date
    if expected.tzinfo is None:
        expected = expected.replace(tzinfo=timezone.utc)

    if now > expected:
        # Define status como atrasado no histórico se entregou tarde (opcional, mas bom para registro)
        # Mas como a flag é 'RETURNED', a multa fica no response.
        overdue_days = (now - expected).days

        if overdue_days > 0:
            fine = overdue_days * DAILY_FINE

    # Atualizar Estoque
    book_query = select(Book).where(Book.id == loan.book_id)
    book_result = await db.execute(book_query)
    book = book_result.scalar_one_or_none()

    if book:
        book.available_copies += 1

    await db.commit()

    # Helper para calcular dias de atraso no retorno
    days_overdue = 0
    if now > expected:
        days_overdue = (now - expected).days

    return {
        "message": "Livro retornado.",
        "loan_id": loan.id,
        "fine_amount": f"R$ {fine:.2f}",
        "days_overdue": max(0, days_overdue),
    }


@router.get("/", response_model=List[LoanResponse])
async def list_loans(
    user_id: Optional[int] = None,
    status: Optional[LoanStatus] = None,  # [RF11] Filtro de Status
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    query = select(Loan)

    if user_id:
        query = query.where(Loan.user_id == user_id)

    if status:
        query = query.where(Loan.status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
