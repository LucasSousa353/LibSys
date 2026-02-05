import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, DateTime, Enum, func, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.base import Base


class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)

    loan_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expected_return_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    return_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    fine_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0.0, nullable=False
    )
    status: Mapped[LoanStatus] = mapped_column(
        Enum(LoanStatus), default=LoanStatus.ACTIVE
    )

    user = relationship("User", back_populates="loans")
    book = relationship("Book", back_populates="loans")
