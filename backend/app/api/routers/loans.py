from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.base import get_db
from app.models.loan import Loan, LoanStatus
from app.models.book import Book
from app.models.user import User
from app.schemas.loan import LoanCreate, LoanResponse

router = APIRouter(prefix="/loans", tags=["Loans"])

# Regras de Negócio Constantes. ToDo exportar pra env
MAX_ACTIVE_LOANS = 3
LOAN_DURATION_DAYS = 14
DAILY_FINE = 2.00

@router.post("/", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=404, detail="Libro não encontrado")
    if book.available_copies < 1:
        raise HTTPException(status_code=400, detail="Livro não disponível no estoque")

    # 2. Verificar usuário
    user_query = select(User).where(User.id == loan_in.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não localizado")

    # 3. Verificar limite de empréstimos ativos do usuário
    active_loans_query = select(func.count(Loan.id)).where(
        Loan.user_id == loan_in.user_id,
        Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
    )
    active_loans_result = await db.execute(active_loans_query)
    active_count = active_loans_result.scalar() or 0

    if active_count >= MAX_ACTIVE_LOANS:
        raise HTTPException(status_code=400, detail=f"Usuário atingiu o limite de {MAX_ACTIVE_LOANS} empréstimos ativos")

    # 4. Criar Empréstimo e Atualizar Estoque
    now = datetime.now(timezone.utc)
    expected_return = now + timedelta(days=LOAN_DURATION_DAYS)

    new_loan = Loan(
        user_id=loan_in.user_id,
        book_id=loan_in.book_id,
        loan_date=now,
        expected_return_date=expected_return,
        status=LoanStatus.ACTIVE
    )
    
    # Decrementa estoque
    book.available_copies -= 1
    
    db.add(new_loan)
    db.add(book)
    
    await db.commit()
    await db.refresh(new_loan)
    return new_loan

# ToDo corrigir tipagem
@router.post("/{loan_id}/return", status_code=status.HTTP_200_OK)
async def return_loan(loan_id: int, db: AsyncSession = Depends(get_db)): # type: ignore
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
    if loan.expected_return_date.tzinfo is None:
        loan.expected_return_date = loan.expected_return_date.replace(tzinfo=timezone.utc)
        
    if now > loan.expected_return_date:
        overdue_days = (now - loan.expected_return_date).days

        if overdue_days > 0:
            fine = overdue_days * DAILY_FINE

    # Atualizar Estoque
    book_query = select(Book).where(Book.id == loan.book_id)
    book_result = await db.execute(book_query)
    book = book_result.scalar_one_or_none()
    
    if book:
        book.available_copies += 1

    await db.commit()
    
    return {
        "message": "Livro retornado.",
        "loan_id": loan.id,
        "fine_amount": f"R$ {fine:.2f}",
        "days_overdue": max(0, (now - loan.expected_return_date).days) if now > loan.expected_return_date else 0
    } # pyright: ignore[reportUnknownVariableType]

@router.get("/", response_model=List[LoanResponse])
async def list_loans(
    user_id: int | None = None,
    skip: int = 0, 
    limit: int = 10, 
    db: AsyncSession = Depends(get_db)
):
    query = select(Loan)
    if user_id:
        query = query.where(Loan.user_id == user_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()