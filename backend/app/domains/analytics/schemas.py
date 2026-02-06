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
    """Indicadores principais do dashboard."""

    total_books: int
    active_loans: int
    overdue_loans: int
    total_fines: Decimal
    recent_books: List[dict]


class ReportsSummary(BaseModel):
    """Indicadores do relatório analítico."""

    total_books: int
    total_users: int
    active_loans: int
    overdue_loans: int
    total_fines: Decimal
    most_borrowed_books: List[MostBorrowedBookItem]
