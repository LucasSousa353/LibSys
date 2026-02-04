from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from redis.asyncio import Redis

from app.db.base import get_db
from app.core.redis import get_redis
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
async def create_loan(
    loan_in: LoanCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis) # [Cache] Injeção para invalidação
):
    """
    Realiza um empréstimo com Lock Pessimista no estoque.
    """

    # 1. Buscar Livro com lock pessimista
    book_query = select(Book).where(Book.id == loan_in.book_id).with_for_update()
    book_result = await db.execute(book_query)
    book = book_result.scalar_one_or_none()

    if not book:
        # Se não achou, rollback
        await db.rollback() 
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    if book.available_copies < 1:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Livro não disponível no estoque")

    # 2. Verificar usuário
    user_query = select(User).where(User.id == loan_in.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if not user:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Usuário não localizado")

    # 3. Verificar limite de empréstimos ativos
    active_loans_query = select(func.count(Loan.id)).where(
        Loan.user_id == loan_in.user_id,
        Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
    )
    active_loans_result = await db.execute(active_loans_query)
    active_count = active_loans_result.scalar() or 0

    if active_count >= MAX_ACTIVE_LOANS:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Usuário atingiu o limite de {MAX_ACTIVE_LOANS} empréstimos ativos",
        )

    # 4. Verificar atrasos (Bloqueio)
    now = datetime.now(timezone.utc)
    overdue_check_query = select(Loan).where(
        Loan.user_id == loan_in.user_id,
        Loan.status == LoanStatus.ACTIVE,
        Loan.expected_return_date < now,
    )
    overdue_check_result = await db.execute(overdue_check_query)
    if overdue_check_result.first():
        await db.rollback()
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

    # Decrementa estoque (Seguro devido ao lock acima)
    book.available_copies -= 1

    db.add(new_loan)
    db.add(book)

    await db.commit()
    await db.refresh(new_loan)

    # 6. [Cache] Invalidar listagem de livros pois o estoque mudou
    # Usamos scan_iter para não bloquear o Redis
    async for key in redis.scan_iter("books:list:*"):
        await redis.delete(key)

    return new_loan


@router.post("/{loan_id}/return", status_code=status.HTTP_200_OK)
async def return_loan(
    loan_id: int, 
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis) # [Cache] Injeção
):
    """
    Processa a devolução e atualiza estoque.
    """
    # Lock no Empréstimo para evitar devolução dupla concorrente
    query = select(Loan).where(Loan.id == loan_id).with_for_update()
    result = await db.execute(query)
    loan = result.scalar_one_or_none()

    if not loan:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status == LoanStatus.RETURNED:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Loan already returned")

    book_query = select(Book).where(Book.id == loan.book_id).with_for_update()
    book_result = await db.execute(book_query)
    book = book_result.scalar_one_or_none()

    # Lógica de Devolução
    now = datetime.now(timezone.utc)
    loan.return_date = now
    loan.status = LoanStatus.RETURNED

    # Cálculo de Multa
    fine = 0.0
    expected = loan.expected_return_date
    if expected.tzinfo is None:
        expected = expected.replace(tzinfo=timezone.utc)

    if now > expected:
        overdue_days = (now - expected).days
        if overdue_days > 0:
            fine = overdue_days * DAILY_FINE

    # Atualizar Estoque
    if book:
        book.available_copies += 1
        db.add(book) # Marca explicitamente para update

    db.add(loan)
    await db.commit()

    # [Cache] Invalidar listagem de livros
    async for key in redis.scan_iter("books:list:*"):
        await redis.delete(key)

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
    status: Optional[LoanStatus] = None,
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