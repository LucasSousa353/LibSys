import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.api.v1.routers.books import create_book, list_books, get_book
from app.domains.books.schemas import BookCreate
from app.domains.books.models import Book


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()

    async def _scan_iter(match):
        if False:
            yield None

    redis.scan_iter.side_effect = _scan_iter
    return redis


@pytest.mark.asyncio
async def test_create_book_success(mock_db_session, mock_redis):
    book_in = BookCreate(title="Unit", author="Auth", isbn="U-1", total_copies=5)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    new_book = await create_book(book_in, db=mock_db_session, redis=mock_redis)

    assert new_book.title == "Unit"
    assert new_book.available_copies == 5
    assert mock_db_session.add.called
    assert mock_redis.scan_iter.called


@pytest.mark.asyncio
async def test_create_book_duplicate_isbn(mock_db_session, mock_redis):
    book_in = BookCreate(title="Dup", author="A", isbn="D-1", total_copies=1)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Book(isbn="D-1")
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await create_book(book_in, db=mock_db_session, redis=mock_redis)

    assert exc.value.status_code == 400
    assert "ISBN já registrado" in exc.value.detail
    assert not mock_db_session.add.called


@pytest.mark.asyncio
async def test_list_books_cache_hit(mock_db_session, mock_redis):
    cached_data = [
        {
            "id": 1,
            "title": "Cached",
            "author": "C",
            "isbn": "C-1",
            "total_copies": 1,
            "available_copies": 1,
        }
    ]
    mock_redis.get.return_value = json.dumps(cached_data)

    result = await list_books(
        title=None, author=None, skip=0, limit=10, db=mock_db_session, redis=mock_redis
    )

    assert len(result) == 1
    assert result[0]["title"] == "Cached"

    assert not mock_db_session.execute.called


@pytest.mark.asyncio
async def test_list_books_cache_miss(mock_db_session, mock_redis):
    mock_redis.get.return_value = None

    db_books = [
        Book(
            id=1,
            title="DB Book",
            author="DB",
            isbn="DB-1",
            total_copies=2,
            available_copies=2,
        )
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = db_books
    mock_db_session.execute.return_value = mock_result

    result = await list_books(
        title=None, author=None, skip=0, limit=10, db=mock_db_session, redis=mock_redis
    )

    assert len(result) == 1
    assert result[0]["title"] == "DB Book"

    assert mock_redis.set.called


@pytest.mark.asyncio
async def test_get_book_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await get_book(999, db=mock_db_session)
    assert exc.value.status_code == 404
