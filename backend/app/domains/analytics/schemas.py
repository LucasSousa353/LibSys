from decimal import Decimal
from typing import List
from pydantic import BaseModel, ConfigDict


class MostBorrowedBookItem(BaseModel):
    """Livro mais emprestado com contagem de empréstimos."""

    book_id: int
    title: str
    author: str
    loan_count: int

    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    """Indicadores unificados do dashboard (métricas + tabelas + gráficos)."""

    total_books: int
    total_users: int
    active_loans: int
    overdue_loans: int
    total_fines: Decimal
    recent_books: List[dict]
    most_borrowed_books: List[MostBorrowedBookItem]
