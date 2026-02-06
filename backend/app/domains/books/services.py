import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.domains.books.models import Book
from app.domains.books.schemas import BookCreate, BookUpdate
from app.core.reports.pdf import PdfTableBuilder
from app.domains.books.repository import BookRepository
from app.core.messages import ErrorMessages
from app.domains.audit.services import AuditLogService


class BookService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.repository = BookRepository(db)

    async def create_book(
        self, book_in: BookCreate, actor_user_id: int | None = None
    ) -> Book:
        """
        Cria um novo livro no sistema.

        Args:
            book_in: Dados do livro a ser criado

        Returns:
            Book: Livro criado

        Raises:
            ValueError: Se ISBN já está registrado
        """
        # Verifica ISBN duplicado
        existing_book = await self.repository.find_by_isbn(book_in.isbn)
        if existing_book:
            raise ValueError(ErrorMessages.BOOK_ISBN_ALREADY_EXISTS)

        # Persiste no banco
        new_book = Book(
            title=book_in.title,
            author=book_in.author,
            isbn=book_in.isbn,
            total_copies=book_in.total_copies,
            available_copies=book_in.total_copies,
        )
        new_book = await self.repository.create(new_book)
        await self.db.flush()

        audit_service = AuditLogService(self.db)
        await audit_service.log_event(
            action="book_created",
            entity_type="book",
            entity_id=new_book.id,
            actor_user_id=actor_user_id,
            level="info",
            message="Book created",
            metadata={"isbn": new_book.isbn},
        )

        # Commit da transação
        await self.db.commit()
        await self.db.refresh(new_book)

        # Invalida cache
        await self._invalidate_books_cache()

        return new_book

    async def update_book(
        self, book_id: int, book_in: BookUpdate, actor_user_id: int | None = None
    ) -> Book:
        """
        Atualiza campos de um livro existente.

        Se total_copies mudar, ajusta available_copies proporcionalmente.

        Raises:
            LookupError: Se livro não encontrado
            ValueError: Se total_copies ficaria menor que cópias emprestadas
        """
        book = await self.repository.find_by_id(book_id)
        if not book:
            raise LookupError(ErrorMessages.BOOK_NOT_FOUND)

        if book_in.title is not None:
            book.title = book_in.title
        if book_in.author is not None:
            book.author = book_in.author
        if book_in.total_copies is not None:
            copies_in_use = book.total_copies - book.available_copies
            if book_in.total_copies < copies_in_use:
                raise ValueError(
                    f"Não é possível reduzir para {book_in.total_copies} cópias, "
                    f"pois {copies_in_use} estão emprestadas"
                )
            book.available_copies += book_in.total_copies - book.total_copies
            book.total_copies = book_in.total_copies

        await self.repository.update(book)
        await self.db.flush()

        audit_service = AuditLogService(self.db)
        await audit_service.log_event(
            action="book_updated",
            entity_type="book",
            entity_id=book.id,
            actor_user_id=actor_user_id,
            level="info",
            message="Book updated",
            metadata={"isbn": book.isbn},
        )

        await self.db.commit()
        await self.db.refresh(book)
        await self._invalidate_books_cache()
        return book

    async def list_books(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> List[Book]:
        """
        Lista livros com filtros opcionais e cache.

        Args:
            title: Filtro parcial por título
            author: Filtro parcial por autor
            skip: Número de registros a pular (paginação)
            limit: Número máximo de registros a retornar

        Returns:
            List[Book]: Lista de livros
        """
        # Monta chave de cache
        t_key = title or ""
        a_key = author or ""
        cache_key = f"books:list:{skip}:{limit}:{t_key}:{a_key}"

        # Tenta buscar do cache
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Cache Miss -> Repository Query
        books = await self.repository.find_all(
            title=title, author=author, skip=skip, limit=limit
        )

        # Cacheia resultado (TTL 60s)
        books_data = [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "isbn": b.isbn,
                "total_copies": b.total_copies,
                "available_copies": b.available_copies,
            }
            for b in books
        ]
        await self.redis.set(cache_key, json.dumps(books_data), ex=60)

        return books  # type: ignore

    async def get_book_by_id(self, book_id: int) -> Book:
        """
        Busca um livro pelo ID.

        Args:
            book_id: ID do livro

        Returns:
            Book: Livro encontrado

        Raises:
            LookupError: Se livro não for encontrado
        """
        book = await self.repository.find_by_id(book_id)

        if not book:
            raise LookupError(ErrorMessages.BOOK_NOT_FOUND)

        return book

    async def _invalidate_books_cache(self):
        """Helper privado para limpar cache de listagem"""
        async for key in self.redis.scan_iter("books:list:*"):
            await self.redis.delete(key)

    async def export_books_pdf_file(
        self,
        file_path: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        batch_size: int = 1000,
    ) -> None:
        """Exporta livros em PDF direto para arquivo."""
        headers = [
            "ID",
            "Title",
            "Author",
            "ISBN",
            "Total",
            "Available",
        ]
        pdf = PdfTableBuilder("Books Export", headers, orientation="L")

        skip = 0
        while True:
            books = await self.repository.find_all(
                title=title, author=author, skip=skip, limit=batch_size
            )
            if not books:
                break

            for book in books:
                pdf.add_row(
                    [
                        str(book.id),
                        book.title,
                        book.author,
                        book.isbn,
                        str(book.total_copies),
                        str(book.available_copies),
                    ]
                )

            skip += batch_size

        pdf.output_to_file(file_path)
