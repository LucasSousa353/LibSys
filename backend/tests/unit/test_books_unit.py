import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.api.v1.routers.books import create_book, list_books, get_book
from app.domains.books.schemas import BookCreate, BookResponse
from app.domains.books.models import Book


class TestBookFixtures:
    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        redis.delete = AsyncMock()

        async def empty_scan_iter(match):
            return
            yield

        redis.scan_iter = empty_scan_iter
        return redis

    @pytest.fixture
    def mock_current_user(self):
        from app.domains.users.models import User

        return User(
            id=1, name="Test User", email="test@test.com", hashed_password="hashed"
        )

    @pytest.fixture
    def sample_book(self):
        return Book(
            id=1,
            title="Clean Code",
            author="Robert Martin",
            isbn="978-0132350884",
            total_copies=5,
            available_copies=5,
        )

    @pytest.fixture
    def sample_book_create(self):
        return BookCreate(
            title="Clean Code",
            author="Robert Martin",
            isbn="978-0132350884",
            total_copies=5,
        )


class TestCreateBook(TestBookFixtures):
    @pytest.mark.asyncio
    async def test_create_book_success(
        self, mock_db_session, mock_redis, mock_current_user, sample_book_create
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        new_book = await create_book(
            sample_book_create, mock_current_user, db=mock_db_session, redis=mock_redis
        )

        assert new_book.title == "Clean Code"
        assert new_book.author == "Robert Martin"
        assert new_book.isbn == "978-0132350884"
        assert new_book.available_copies == 5
        assert new_book.total_copies == 5
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_book_duplicate_isbn_raises_400(
        self,
        mock_db_session,
        mock_redis,
        mock_current_user,
        sample_book_create,
        sample_book,
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await create_book(
                sample_book_create,
                mock_current_user,
                db=mock_db_session,
                redis=mock_redis,
            )

        assert exc.value.status_code == 400
        assert "ISBN já registrado" in exc.value.detail
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_book_sets_available_copies_equal_to_total(
        self, mock_db_session, mock_redis, mock_current_user
    ):
        book_in = BookCreate(
            title="Test", author="Author", isbn="TEST-123", total_copies=10
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        new_book = await create_book(
            book_in, mock_current_user, db=mock_db_session, redis=mock_redis
        )

        assert new_book.available_copies == new_book.total_copies == 10

    @pytest.mark.asyncio
    async def test_create_book_with_minimum_copies(
        self, mock_db_session, mock_redis, mock_current_user
    ):
        book_in = BookCreate(
            title="Single Copy", author="Author", isbn="MIN-001", total_copies=1
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        new_book = await create_book(
            book_in, mock_current_user, db=mock_db_session, redis=mock_redis
        )

        assert new_book.total_copies == 1
        assert new_book.available_copies == 1


class TestListBooks(TestBookFixtures):
    @pytest.mark.asyncio
    async def test_list_books_returns_from_cache_when_hit(
        self, mock_db_session, mock_redis
    ):
        cached_books = [
            {
                "id": 1,
                "title": "Cached Book",
                "author": "Cache Author",
                "isbn": "CACHE-001",
                "total_copies": 3,
                "available_copies": 2,
            }
        ]
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_books))

        result = await list_books(
            title=None,
            author=None,
            skip=0,
            limit=10,
            db=mock_db_session,
            redis=mock_redis,
        )

        assert len(result) == 1
        assert result[0]["title"] == "Cached Book"
        mock_db_session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_list_books_queries_db_on_cache_miss(
        self, mock_db_session, mock_redis, sample_book
    ):
        mock_redis.get = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_book]
        mock_db_session.execute.return_value = mock_result

        result = await list_books(
            title=None,
            author=None,
            skip=0,
            limit=10,
            db=mock_db_session,
            redis=mock_redis,
        )

        assert len(result) == 1
        assert result[0].title == "Clean Code"
        mock_db_session.execute.assert_awaited_once()
        mock_redis.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_books_with_title_filter(
        self, mock_db_session, mock_redis, sample_book
    ):
        mock_redis.get = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_book]
        mock_db_session.execute.return_value = mock_result

        result = await list_books(
            title="Clean",
            author=None,
            skip=0,
            limit=10,
            db=mock_db_session,
            redis=mock_redis,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_books_with_author_filter(
        self, mock_db_session, mock_redis, sample_book
    ):
        mock_redis.get = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_book]
        mock_db_session.execute.return_value = mock_result

        result = await list_books(
            title=None,
            author="Robert",
            skip=0,
            limit=10,
            db=mock_db_session,
            redis=mock_redis,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_books_empty_result(self, mock_db_session, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await list_books(
            title=None,
            author=None,
            skip=0,
            limit=10,
            db=mock_db_session,
            redis=mock_redis,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_list_books_pagination_skip(self, mock_db_session, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        await list_books(
            title=None,
            author=None,
            skip=10,
            limit=5,
            db=mock_db_session,
            redis=mock_redis,
        )

        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_books_cache_key_includes_filters(
        self, mock_db_session, mock_redis, sample_book
    ):
        mock_redis.get = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_book]
        mock_db_session.execute.return_value = mock_result

        await list_books(
            title="Clean",
            author="Martin",
            skip=0,
            limit=10,
            db=mock_db_session,
            redis=mock_redis,
        )

        call_args = mock_redis.set.call_args
        cache_key = call_args[0][0]
        assert "Clean" in cache_key
        assert "Martin" in cache_key


class TestGetBook(TestBookFixtures):
    @pytest.mark.asyncio
    async def test_get_book_found(self, mock_db_session, sample_book):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_db_session.execute.return_value = mock_result

        result = await get_book(1, db=mock_db_session)

        assert result.id == 1
        assert result.title == "Clean Code"
        assert result.author == "Robert Martin"

    @pytest.mark.asyncio
    async def test_get_book_not_found_raises_404(self, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_book(999, db=mock_db_session)

        assert exc.value.status_code == 404
        assert "Livro não encontrado" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_book_with_zero_id(self, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_book(0, db=mock_db_session)

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_book_with_negative_id(self, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_book(-1, db=mock_db_session)

        assert exc.value.status_code == 404
