import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_create_book_success(client):
    payload = {
        "title": "Integration Book",
        "author": "Test Author",
        "isbn": "INT-001",
        "total_copies": 10,
    }
    response = await client.post("/books/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["available_copies"] == 10
    assert "id" in data


@pytest.mark.asyncio
async def test_create_book_duplicate_isbn(client):
    payload = {
        "title": "Book 1",
        "author": "Author 1",
        "isbn": "DUP-001",
        "total_copies": 5,
    }
    resp1 = await client.post("/books/", json=payload)
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = await client.post("/books/", json=payload)
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert "ISBN já registrado" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_get_book_not_found(client):
    response = await client.get("/books/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_list_books_pagination_and_cache(client):
    for i in range(3):
        await client.post(
            "/books/",
            json={
                "title": f"Book {i}",
                "author": "Auth",
                "isbn": f"CACHE-{i}",
                "total_copies": 1,
            },
        )

    resp1 = await client.get("/books/?limit=2")
    assert resp1.status_code == status.HTTP_200_OK
    assert len(resp1.json()) >= 2

    resp2 = await client.get("/books/?limit=2")
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json() == resp1.json()
