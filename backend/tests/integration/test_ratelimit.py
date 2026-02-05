import pytest
from httpx import AsyncClient

from tests.factories import BookFactory


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_loans_endpoint_allows_five_requests(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        book = await create_book(total_copies=100, available_copies=100)
        loan_payload = {"user_id": authenticated_user.id, "book_id": book.id}
        for _ in range(5):
            response = await client.post("/loans/", json=loan_payload)
            assert response.status_code != 429

    @pytest.mark.asyncio
    async def test_rate_limit_loans_endpoint_blocks_sixth_request(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        book = await create_book(total_copies=100, available_copies=100)
        loan_payload = {"user_id": authenticated_user.id, "book_id": book.id}
        for _ in range(5):
            await client.post("/loans/", json=loan_payload)
        response = await client.post("/loans/", json=loan_payload)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_does_not_apply_to_other_endpoints(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        await create_book()
        for _ in range(10):
            response = await client.get("/books/")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_per_user(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        book = await create_book(total_copies=100, available_copies=100)
        loan_payload = {"user_id": authenticated_user.id, "book_id": book.id}
        for _ in range(5):
            await client.post("/loans/", json=loan_payload)
        response = await client.post("/loans/", json=loan_payload)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_returns_proper_error_message(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        book = await create_book(total_copies=100, available_copies=100)
        loan_payload = {"user_id": authenticated_user.id, "book_id": book.id}
        for _ in range(5):
            await client.post("/loans/", json=loan_payload)
        response = await client.post("/loans/", json=loan_payload)
        assert response.status_code == 429
        assert "detail" in response.json()
