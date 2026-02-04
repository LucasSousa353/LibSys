import pytest
import json
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
async def test_get_book_lifecycle(client):
    payload = {
        "title": "Find Me",
        "author": "Seeker",
        "isbn": "FIND-001",
        "total_copies": 1,
    }
    create_resp = await client.post("/books/", json=payload)
    book_id = create_resp.json()["id"]

    resp = await client.get(f"/books/{book_id}")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["isbn"] == "FIND-001"

    resp_nf = await client.get("/books/99999")
    assert resp_nf.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_list_books_filtering(client):
    b1 = {
        "title": "Python Basics",
        "author": "Guido",
        "isbn": "PY-1",
        "total_copies": 5,
    }
    b2 = {
        "title": "Java Master",
        "author": "Gosling",
        "isbn": "JV-1",
        "total_copies": 3,
    }
    await client.post("/books/", json=b1)
    await client.post("/books/", json=b2)

    resp = await client.get("/books/?title=Python")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["isbn"] == "PY-1"

    resp = await client.get("/books/?author=gosling")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["isbn"] == "JV-1"


@pytest.mark.asyncio
async def test_cache_hit_and_invalidation(client, redis_client_test):
    await client.post(
        "/books/",
        json={"title": "B1", "author": "A1", "isbn": "C-1", "total_copies": 1},
    )

    await client.get("/books/")

    keys = await redis_client_test.keys("books:list:*")
    assert len(keys) > 0, "Deveria ter criado chave de cache"

    cache_key = keys[0]
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

    resp_cached = await client.get("/books/")
    assert resp_cached.json()[0]["title"] == "Cached Title", (
        "Deveria ter retornado o valor do cache"
    )

    await client.post(
        "/books/",
        json={"title": "B2", "author": "A2", "isbn": "C-2", "total_copies": 1},
    )

    keys_after = await redis_client_test.keys("books:list:*")
    assert len(keys_after) == 0, "Cache deveria ter sido invalidado após POST"

    resp_fresh = await client.get("/books/")
    data = resp_fresh.json()

    titles = [b["title"] for b in data]
    assert "B1" in titles
    assert "B2" in titles
