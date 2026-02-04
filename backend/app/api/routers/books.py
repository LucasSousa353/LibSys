from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.base import get_db
from app.models.book import Book
from app.schemas.book import BookCreate, BookResponse

router = APIRouter(prefix="/books", tags=["Books"])

@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate, db: AsyncSession = Depends(get_db)):
    # Verifica ISBN duplicado
    query = select(Book).where(Book.isbn == book.isbn)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="ISBN já registrado")
    
    new_book = Book(
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        total_copies=book.total_copies,
        available_copies=book.total_copies 
    )
    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)
    return new_book

@router.get("/", response_model=List[BookResponse])
async def list_books(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    query = select(Book).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    query = select(Book).where(Book.id == book_id)
    result = await db.execute(query)
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return book