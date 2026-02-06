from typing import Annotated, List, Optional
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.base import get_db
from app.core.cache.redis import get_redis
from app.core.config import settings
from app.domains.auth.dependencies import get_current_user
from app.domains.books.schemas import BookCreate, BookResponse
from app.domains.books.services import BookService
from app.domains.users.models import User

router = APIRouter(prefix="/books", tags=["Books"])


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book: BookCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    service = BookService(db=db, redis=redis)
    try:
        new_book = await service.create_book(book)
        return new_book
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[BookResponse])
async def list_books(
    title: Optional[str] = Query(None, description="Filtrar por título (parcial)"),
    author: Optional[str] = Query(None, description="Filtrar por autor (parcial)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    service = BookService(db=db, redis=redis)
    books = await service.list_books(title=title, author=author, skip=skip, limit=limit)
    return books


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int, db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)
):
    service = BookService(db=db, redis=redis)
    try:
        book = await service.get_book_by_id(book_id)
        return book
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/export/pdf")
async def export_books_pdf(
    title: Optional[str] = Query(None, description="Filtrar por titulo (parcial)"),
    author: Optional[str] = Query(None, description="Filtrar por autor (parcial)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    service = BookService(db=db, redis=redis)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_file.close()
    await service.export_books_pdf_file(temp_file.name, title=title, author=author)
    background_tasks.add_task(os.unlink, temp_file.name)
    return FileResponse(
        temp_file.name,
        media_type="application/pdf",
        filename="books.pdf",
        background=background_tasks,
    )
