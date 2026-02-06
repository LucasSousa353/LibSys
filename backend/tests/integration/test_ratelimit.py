import pytest
from httpx import AsyncClient


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_loans_endpoint_allows_five_requests(
        self, client: AsyncClient, create_book, create_user
    ):
        book = await create_book(total_copies=100, available_copies=100)
        user_ids = [(await create_user(email=f"rate{i}@test.com")).id for i in range(5)]

        for idx in range(5):
            response = await client.post(
                "/loans/", json={"user_id": user_ids[idx], "book_id": book.id}
            )
            assert response.status_code != 429

    @pytest.mark.asyncio
    async def test_rate_limit_loans_endpoint_blocks_sixth_request(
        self, client: AsyncClient, create_book, create_user
    ):
        book = await create_book(total_copies=100, available_copies=100)
        user_ids = [
            (await create_user(email=f"rate{i}@block.com")).id for i in range(6)
        ]

        for idx in range(5):
            await client.post(
                "/loans/", json={"user_id": user_ids[idx], "book_id": book.id}
            )
        response = await client.post(
            "/loans/", json={"user_id": user_ids[5], "book_id": book.id}
        )
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
        self, client: AsyncClient, create_book, create_user
    ):
        book = await create_book(total_copies=100, available_copies=100)
        user_ids = [(await create_user(email=f"rate{i}@per.com")).id for i in range(6)]

        for idx in range(5):
            await client.post(
                "/loans/", json={"user_id": user_ids[idx], "book_id": book.id}
            )
        response = await client.post(
            "/loans/", json={"user_id": user_ids[5], "book_id": book.id}
        )
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_returns_proper_error_message(
        self, client: AsyncClient, create_book, create_user
    ):
        book = await create_book(total_copies=100, available_copies=100)
        user_ids = [(await create_user(email=f"rate{i}@msg.com")).id for i in range(6)]

        for idx in range(5):
            await client.post(
                "/loans/", json={"user_id": user_ids[idx], "book_id": book.id}
            )
        response = await client.post(
            "/loans/", json={"user_id": user_ids[5], "book_id": book.id}
        )
        assert response.status_code == 429
        assert "detail" in response.json()
