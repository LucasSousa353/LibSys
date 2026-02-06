import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.books.models import Book
from app.domains.books.schemas import BookCreate
from app.domains.books.services import BookService
from app.core.messages import ErrorMessages


class TestBookServiceFixtures:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.flush = AsyncMock()
        return db

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
    def service(self, mock_db, mock_redis):
        service = BookService(db=mock_db, redis=mock_redis)
        service.repository = MagicMock()
        service.repository.find_by_isbn = AsyncMock()
        service.repository.find_all = AsyncMock()
        service.repository.find_by_id = AsyncMock()
        service.repository.create = AsyncMock()
        service.repository.update = AsyncMock()
        return service

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


class TestCreateBook(TestBookServiceFixtures):
    @pytest.mark.asyncio
    async def test_create_book_success(self, service, mock_db, sample_book):
        service.repository.find_by_isbn.return_value = None
        service.repository.create.return_value = sample_book

        with patch(
            "app.domains.books.services.AuditLogService.log_event", new=AsyncMock()
        ):
            book = await service.create_book(
                BookCreate(
                    title="Clean Code",
                    author="Robert Martin",
                    isbn="978-0132350884",
                    total_copies=5,
                )
            )

        assert book.title == "Clean Code"
        assert book.available_copies == 5
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_book_duplicate_isbn_raises_value_error(
        self, service, sample_book
    ):
        service.repository.find_by_isbn.return_value = sample_book

        with pytest.raises(ValueError) as exc:
            await service.create_book(
                BookCreate(
                    title="Clean Code",
                    author="Robert Martin",
                    isbn="978-0132350884",
                    total_copies=5,
                )
            )

        assert ErrorMessages.BOOK_ISBN_ALREADY_EXISTS in str(exc.value)


class TestListBooks(TestBookServiceFixtures):
    @pytest.mark.asyncio
    async def test_list_books_cache_hit_returns_cached_data(self, service, mock_redis):
        cached = [
            {
                "id": 1,
                "title": "Cached",
                "author": "Author",
                "isbn": "CACHE-001",
                "total_copies": 2,
                "available_copies": 2,
            }
        ]
        mock_redis.get.return_value = json.dumps(cached)

        result = await service.list_books(title=None, author=None, skip=0, limit=10)

        assert result == cached
        service.repository.find_all.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_list_books_cache_miss_queries_repo(
        self, service, sample_book, mock_redis
    ):
        mock_redis.get.return_value = None
        service.repository.find_all.return_value = [sample_book]

        result = await service.list_books(title=None, author=None, skip=0, limit=10)

        assert len(result) == 1
        assert result[0].title == "Clean Code"
        service.repository.find_all.assert_awaited_once()
        mock_redis.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_books_cache_key_includes_filters(
        self, service, mock_redis, sample_book
    ):
        mock_redis.get.return_value = None
        service.repository.find_all.return_value = [sample_book]

        await service.list_books(title="Clean", author="Martin", skip=0, limit=10)

        cache_key = mock_redis.set.call_args[0][0]
        assert "Clean" in cache_key
        assert "Martin" in cache_key


class TestGetBook(TestBookServiceFixtures):
    @pytest.mark.asyncio
    async def test_get_book_by_id_success(self, service, sample_book):
        service.repository.find_by_id.return_value = sample_book

        book = await service.get_book_by_id(1)

        assert book.id == 1
        assert book.title == "Clean Code"

    @pytest.mark.asyncio
    async def test_get_book_by_id_not_found(self, service):
        service.repository.find_by_id.return_value = None

        with pytest.raises(LookupError) as exc:
            await service.get_book_by_id(999)

        assert ErrorMessages.BOOK_NOT_FOUND in str(exc.value)


class TestInvalidateBooksCache(TestBookServiceFixtures):
    @pytest.mark.asyncio
    async def test_invalidate_books_cache_deletes_keys(self, service, mock_redis):
        async def scan_iter(match):
            for key in ["books:list:0:10::", "books:list:0:10:title:"]:
                yield key

        mock_redis.scan_iter = scan_iter

        await service._invalidate_books_cache()

        assert mock_redis.delete.await_count == 2
