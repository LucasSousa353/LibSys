from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.base import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    author: Mapped[str] = mapped_column(String, index=True, nullable=False)
    isbn: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    # Controle de estoque
    total_copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    available_copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    loans = relationship("Loan", back_populates="book")
