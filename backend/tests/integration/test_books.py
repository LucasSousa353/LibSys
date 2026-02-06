import pytest
import json
from httpx import AsyncClient


class TestCreateBook:
    @pytest.fixture
    def valid_book_data(self):
        return {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "978-0132350884",
            "total_copies": 5,
        }

    @pytest.mark.asyncio
    async def test_create_book_success(self, client: AsyncClient, valid_book_data):
        response = await client.post("/books/", json=valid_book_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == valid_book_data["title"]
        assert data["author"] == valid_book_data["author"]
        assert data["isbn"] == valid_book_data["isbn"]
        assert data["total_copies"] == valid_book_data["total_copies"]
        assert data["available_copies"] == valid_book_data["total_copies"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_book_duplicate_isbn(
        self, client: AsyncClient, valid_book_data
    ):
        await client.post("/books/", json=valid_book_data)
        response = await client.post("/books/", json=valid_book_data)
        assert response.status_code == 400
        assert "ISBN já registrado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_book_requires_staff(
        self, client_user: AsyncClient, valid_book_data
    ):
        response = await client_user.post("/books/", json=valid_book_data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_book_requires_authentication(
        self, client_unauthenticated: AsyncClient, valid_book_data
    ):
        response = await client_unauthenticated.post("/books/", json=valid_book_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_book_missing_title(self, client: AsyncClient):
        response = await client.post(
            "/books/", json={"author": "Author", "isbn": "123-456", "total_copies": 1}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_book_missing_author(self, client: AsyncClient):
        response = await client.post(
            "/books/", json={"title": "Title", "isbn": "123-456", "total_copies": 1}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_book_missing_isbn(self, client: AsyncClient):
        response = await client.post(
            "/books/", json={"title": "Title", "author": "Author", "total_copies": 1}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_book_default_total_copies(self, client: AsyncClient):
        response = await client.post(
            "/books/", json={"title": "Title", "author": "Author", "isbn": "123-456"}
        )
        assert response.status_code == 201
        assert response.json()["total_copies"] == 1
        assert response.json()["available_copies"] == 1

    @pytest.mark.asyncio
    async def test_create_book_negative_total_copies(self, client: AsyncClient):
        response = await client.post(
            "/books/",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "123-456",
                "total_copies": -1,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_book_zero_total_copies(self, client: AsyncClient):
        response = await client.post(
            "/books/",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "123-456",
                "total_copies": 0,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_book_empty_title(self, client: AsyncClient):
        response = await client.post(
            "/books/",
            json={
                "title": "",
                "author": "Author",
                "isbn": "123-456",
                "total_copies": 1,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_book_empty_author(self, client: AsyncClient):
        response = await client.post(
            "/books/",
            json={"title": "Title", "author": "", "isbn": "123-456", "total_copies": 1},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_book_invalid_total_copies_type(self, client: AsyncClient):
        response = await client.post(
            "/books/",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "123-456",
                "total_copies": "abc",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_book_large_total_copies(self, client: AsyncClient):
        response = await client.post(
            "/books/",
            json={
                "title": "Title",
                "author": "Author",
                "isbn": "123-456-lg",
                "total_copies": 10000,
            },
        )
        assert response.status_code == 201
        assert response.json()["total_copies"] == 10000


class TestGetBook:
    @pytest.mark.asyncio
    async def test_get_book_success(self, client: AsyncClient, create_book):
        book = await create_book(
            title="Test Book", author="Test Author", isbn="test-isbn-123"
        )
        response = await client.get(f"/books/{book.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book.id
        assert data["title"] == book.title
        assert data["author"] == book.author

    @pytest.mark.asyncio
    async def test_get_book_not_found(self, client: AsyncClient):
        response = await client.get("/books/99999")
        assert response.status_code == 404
        assert "Livro não encontrado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_book_invalid_id_type(self, client: AsyncClient):
        response = await client.get("/books/abc")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_book_negative_id(self, client: AsyncClient):
        response = await client.get("/books/-1")
        assert response.status_code in [404, 422]


class TestListBooks:
    @pytest.mark.asyncio
    async def test_list_books_empty(self, client: AsyncClient):
        response = await client.get("/books/")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_books_default_pagination(
        self, client: AsyncClient, create_book
    ):
        for i in range(15):
            await create_book()
        response = await client.get("/books/")
        assert response.status_code == 200
        assert len(response.json()) == 10

    @pytest.mark.asyncio
    async def test_list_books_custom_limit(self, client: AsyncClient, create_book):
        for _ in range(15):
            await create_book()
        response = await client.get("/books/?limit=5")
        assert response.status_code == 200
        assert len(response.json()) == 5

    @pytest.mark.asyncio
    async def test_list_books_custom_skip(self, client: AsyncClient, create_book):
        for _ in range(15):
            await create_book()
        response = await client.get("/books/?skip=10")
        assert response.status_code == 200
        assert len(response.json()) == 5

    @pytest.mark.asyncio
    async def test_list_books_skip_and_limit(self, client: AsyncClient, create_book):
        for _ in range(15):
            await create_book()
        response = await client.get("/books/?skip=5&limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_list_books_skip_beyond_total(self, client: AsyncClient, create_book):
        for _ in range(15):
            await create_book()
        response = await client.get("/books/?skip=100")
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_list_books_limit_greater_than_total(
        self, client: AsyncClient, create_book
    ):
        for _ in range(15):
            await create_book()
        response = await client.get("/books/?limit=100")
        assert response.status_code == 200
        assert len(response.json()) == 15

    @pytest.mark.asyncio
    async def test_list_books_limit_above_max_returns_422(self, client: AsyncClient):
        response = await client.get("/books/?limit=101")
        assert response.status_code == 422


class TestListBooksFiltering:
    @pytest.fixture
    async def books_for_filter(self, create_book):
        await create_book(
            title="Python Basics", author="Guido van Rossum", isbn="PY-001"
        )
        await create_book(
            title="Advanced Python", author="David Beazley", isbn="PY-002"
        )
        await create_book(
            title="Java Programming", author="James Gosling", isbn="JV-001"
        )
        await create_book(
            title="JavaScript Guide", author="Douglas Crockford", isbn="JS-001"
        )
        await create_book(title="Clean Code", author="Robert Martin", isbn="CC-001")

    @pytest.mark.asyncio
    async def test_filter_by_title_exact(self, client: AsyncClient, books_for_filter):
        response = await client.get("/books/?title=Python Basics")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["title"] == "Python Basics"

    @pytest.mark.asyncio
    async def test_filter_by_title_partial(self, client: AsyncClient, books_for_filter):
        response = await client.get("/books/?title=Python")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_filter_by_title_case_insensitive(
        self, client: AsyncClient, books_for_filter
    ):
        response = await client.get("/books/?title=python")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_filter_by_author_exact(self, client: AsyncClient, books_for_filter):
        response = await client.get("/books/?author=Robert Martin")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_filter_by_author_partial(
        self, client: AsyncClient, books_for_filter
    ):
        response = await client.get("/books/?author=Guido")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_filter_by_author_case_insensitive(
        self, client: AsyncClient, books_for_filter
    ):
        response = await client.get("/books/?author=gosling")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_filter_by_title_and_author(
        self, client: AsyncClient, books_for_filter
    ):
        response = await client.get("/books/?title=Python&author=Guido")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["title"] == "Python Basics"

    @pytest.mark.asyncio
    async def test_filter_no_match(self, client: AsyncClient, books_for_filter):
        response = await client.get("/books/?title=Nonexistent")
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_filter_with_pagination(self, client: AsyncClient, books_for_filter):
        response = await client.get("/books/?title=Python&skip=0&limit=1")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestBookCache:
    @pytest.mark.asyncio
    async def test_list_books_populates_cache(
        self, client: AsyncClient, create_book, redis_client_test
    ):
        await create_book()
        await redis_client_test.flushdb()
        keys_before = await redis_client_test.keys("books:list:*")
        assert len(keys_before) == 0
        await client.get("/books/")
        keys_after = await redis_client_test.keys("books:list:*")
        assert len(keys_after) > 0

    @pytest.mark.asyncio
    async def test_list_books_uses_cache(
        self, client: AsyncClient, create_book, redis_client_test
    ):
        await create_book()
        await redis_client_test.flushdb()
        await client.get("/books/")
        cache_key = (await redis_client_test.keys("books:list:*"))[0]
        cached_val = [
            {
                "title": "Cached Title",
                "author": "Cached",
                "isbn": "fake",
                "total_copies": 10,
                "available_copies": 10,
                "id": 999,
            }
        ]
        await redis_client_test.set(cache_key, json.dumps(cached_val))
        response = await client.get("/books/")
        assert response.json()[0]["title"] == "Cached Title"

    @pytest.mark.asyncio
    async def test_create_book_invalidates_cache(
        self, client: AsyncClient, create_book, redis_client_test
    ):
        await create_book()
        await redis_client_test.flushdb()
        await redis_client_test.set("other:cache:key", "keep")
        await client.get("/books/")
        keys_after_list = await redis_client_test.keys("books:list:*")
        assert len(keys_after_list) > 0
        await client.post(
            "/books/",
            json={
                "title": "New Book",
                "author": "New Author",
                "isbn": "new-isbn-123",
                "total_copies": 2,
            },
        )
        keys_after_create = await redis_client_test.keys("books:list:*")
        assert len(keys_after_create) == 0
        assert await redis_client_test.get("other:cache:key") == "keep"

    @pytest.mark.asyncio
    async def test_cache_key_varies_by_pagination(
        self, client: AsyncClient, create_book, redis_client_test
    ):
        await create_book()
        await redis_client_test.flushdb()
        await client.get("/books/?skip=0&limit=10")
        await client.get("/books/?skip=0&limit=5")
        await client.get("/books/?skip=5&limit=10")
        keys = await redis_client_test.keys("books:list:*")
        assert len(keys) == 3

    @pytest.mark.asyncio
    async def test_cache_key_varies_by_filter(
        self, client: AsyncClient, create_book, redis_client_test
    ):
        await create_book()
        await redis_client_test.flushdb()
        await client.get("/books/")
        await client.get("/books/?title=Test")
        await client.get("/books/?author=Author")
        await client.get("/books/?title=Test&author=Author")
        keys = await redis_client_test.keys("books:list:*")
        assert len(keys) == 4

    @pytest.mark.asyncio
    async def test_cache_fresh_data_after_invalidation(
        self, client: AsyncClient, create_book, redis_client_test
    ):
        book = await create_book(title="Cached Book")
        await redis_client_test.flushdb()
        await client.get("/books/")
        await client.post(
            "/books/",
            json={
                "title": "Fresh Book",
                "author": "Fresh Author",
                "isbn": "fresh-isbn",
                "total_copies": 1,
            },
        )
        response = await client.get("/books/")
        titles = [b["title"] for b in response.json()]
        assert "Cached Book" in titles
        assert "Fresh Book" in titles


class TestExportBooksPdf:
    @pytest.mark.asyncio
    async def test_export_books_pdf_requires_auth(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get("/books/export/pdf")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_books_pdf_requires_staff(self, client_user: AsyncClient):
        response = await client_user.get("/books/export/pdf")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_export_books_pdf_success(self, client: AsyncClient, create_book):
        await create_book(title="PDF Book")
        response = await client.get("/books/export/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
