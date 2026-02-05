import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis

from app.domains.books.models import Book
from app.domains.books.schemas import BookCreate


class BookService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def create_book(self, book_in: BookCreate) -> Book:
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
        query = select(Book).where(Book.isbn == book_in.isbn)
        result = await self.db.execute(query)
        if result.scalar_one_or_none():
            raise ValueError("ISBN já registrado")

        # Persiste no banco
        new_book = Book(
            title=book_in.title,
            author=book_in.author,
            isbn=book_in.isbn,
            total_copies=book_in.total_copies,
            available_copies=book_in.total_copies,
        )
        self.db.add(new_book)
        await self.db.commit()
        await self.db.refresh(new_book)

        # Invalida cache
        await self._invalidate_books_cache()

        return new_book

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
            # Retorna dados serializados do cache
            # Nota: Router precisará converter de volta para modelos
            return json.loads(cached_data)

        # Cache Miss -> DB Query
        query = select(Book)

        if title:
            query = query.where(Book.title.ilike(f"%{title}%"))
        if author:
            query = query.where(Book.author.ilike(f"%{author}%"))

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        books = result.scalars().all()

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

        return books # type: ignore

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
        query = select(Book).where(Book.id == book_id)
        result = await self.db.execute(query)
        book = result.scalar_one_or_none()
        
        if not book:
            raise LookupError("Livro não encontrado")
            
        return book

    async def _invalidate_books_cache(self):
        """Helper privado para limpar cache de listagem"""
        async for key in self.redis.scan_iter("books:list:*"):
            await self.redis.delete(key)
