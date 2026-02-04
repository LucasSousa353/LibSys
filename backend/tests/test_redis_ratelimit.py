import pytest
from fastapi import status
from sqlalchemy import text


@pytest.mark.asyncio
async def test_rate_limiting_loans(client):
    """
    Testa se o Rate Limit de 5 reqs/minuto está funcionando na rota de empréstimos.
    """
    # 1. Setup
    user_resp = await client.post(
        "/users/", json={"name": "Spammer", "email": "spam@btg.com"}
    )
    user_id = user_resp.json()["id"]

    book_resp = await client.post(
        "/books/",
        json={
            "title": "Spam Book",
            "author": "Bot",
            "isbn": "9999",
            "total_copies": 10,
        },
    )
    book_id = book_resp.json()["id"]

    loan_payload = {"user_id": user_id, "book_id": book_id}

    # 2. Consumir as 5 requisições permitidas
    for _ in range(5):
        response = await client.post("/loans/", json=loan_payload)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

    # 3. A 6ª deve ser bloqueada (429)
    response = await client.post("/loans/", json=loan_payload)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_cache_and_invalidation(
    client, db_session, redis_client_test
):  # <--- Injeta a fixture aqui
    """
    Testa: Cache Hit e Cache Invalidation.
    """
    # Usamos a fixture redis_client_test em vez do global
    await redis_client_test.flushdb()

    # 1. Criar Livro A
    await client.post(
        "/books/",
        json={"title": "Book A", "author": "A", "isbn": "111", "total_copies": 1},
    )

    # 2. Primeira consulta (Popula Cache)
    resp1 = await client.get("/books/")
    assert len(resp1.json()) == 1

    # 3. Inserir Livro B direto no DB (Bypass Cache)
    await db_session.execute(
        text(
            "INSERT INTO books (title, author, isbn, total_copies, available_copies) VALUES ('Book B', 'B', '222', 1, 1)"
        )
    )
    await db_session.commit()

    # 4. Consulta (Deve vir do Cache -> Ignora Book B)
    resp2 = await client.get("/books/")
    data2 = resp2.json()
    assert len(data2) == 1
    assert data2[0]["title"] == "Book A"

    # 5. Criar Livro C via API (Trigger Invalidação)
    await client.post(
        "/books/",
        json={"title": "Book C", "author": "C", "isbn": "333", "total_copies": 1},
    )

    # 6. Consulta Final (Cache limpo -> Traz tudo)
    resp3 = await client.get("/books/")
    data3 = resp3.json()
    assert len(data3) == 3
