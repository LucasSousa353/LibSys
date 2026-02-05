from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.books.models import Book


class BookRepository:
    """Repository para isolamento de queries de Books."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, book_id: int) -> Optional[Book]:
        """Busca um livro por ID."""
        query = select(Book).where(Book.id == book_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_by_isbn(self, isbn: str) -> Optional[Book]:
        """Busca um livro por ISBN."""
        query = select(Book).where(Book.isbn == isbn)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_all(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> List[Book]:
        """
        Lista livros com filtros opcionais e paginação.

        Args:
            title: Filtro parcial por título (case-insensitive)
            author: Filtro parcial por autor (case-insensitive)
            skip: Número de registros a pular
            limit: Número máximo de registros a retornar

        Returns:
            List[Book]: Lista de livros encontrados
        """
        query = select(Book)

        if title:
            query = query.where(Book.title.ilike(f"%{title}%"))
        if author:
            query = query.where(Book.author.ilike(f"%{author}%"))

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore

    async def create(self, book: Book) -> Book:
        """Adiciona um novo livro à sessão (sem commit)."""
        self.db.add(book)
        return book

    async def update(self, book: Book) -> Book:
        """Atualiza um livro existente (sem commit)."""
        self.db.add(book)
        return book

    async def find_by_id_with_lock(self, book_id: int) -> Optional[Book]:
        """
        Busca um livro por ID com lock pessimista.

        Usado em operações concorrentes como empréstimos.
        """
        query = select(Book).where(Book.id == book_id).with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
