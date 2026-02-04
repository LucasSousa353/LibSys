import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis

from app.core.base import get_db
from app.core.redis import get_redis
from app.books.models import Book
from app.books.schemas import BookCreate, BookResponse

router = APIRouter(prefix="/books", tags=["Books"])


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book: BookCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    # 1. Verifica ISBN duplicado
    query = select(Book).where(Book.isbn == book.isbn)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="ISBN já registrado")

    # 2. Persiste no Postgres
    new_book = Book(
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        total_copies=book.total_copies,
        available_copies=book.total_copies,
    )
    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)

    # 3. Invalida cache (Remove todas as variações de filtros e páginas)
    async for key in redis.scan_iter("books:list:*"):
        await redis.delete(key)

    return new_book


@router.get("/", response_model=List[BookResponse])
async def list_books(
    title: Optional[str] = Query(None, description="Filtrar por título (parcial)"),
    author: Optional[str] = Query(None, description="Filtrar por autor (parcial)"),
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):

    t_key = title or ""
    a_key = author or ""
    cache_key = f"books:list:{skip}:{limit}:{t_key}:{a_key}"

    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # 2. Cache Miss -> DB Query
    query = select(Book)

    if title:
        # ilike = Case insensitive search
        query = query.where(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.where(Book.author.ilike(f"%{author}%"))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    books = result.scalars().all()

    books_data = [BookResponse.model_validate(b).model_dump() for b in books]

    # 3. Write cache (TTL 60s)
    await redis.set(cache_key, json.dumps(books_data), ex=60)

    return books_data


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    query = select(Book).where(Book.id == book_id)
    result = await db.execute(query)
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return book
