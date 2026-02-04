import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_rate_limiting_loans_endpoint(client):
    """
    Testa se o Rate Limit de 5 reqs/minuto está funcionando na rota de empréstimos.
    """
    # 1. Setup
    user_resp = await client.post(
        "/users/",
        json={"name": "Spammer", "email": "spam@btg.com", "password": "pass123"},
    )
    user_id = user_resp.json()["id"]

    book_resp = await client.post(
        "/books/",
        json={
            "title": "Spam Book",
            "author": "Bot",
            "isbn": "SPAM-1",
            "total_copies": 100,
        },
    )
    book_id = book_resp.json()["id"]

    loan_payload = {"user_id": user_id, "book_id": book_id}

    # 2. Consumir as 5 requisições permitidas
    for i in range(5):
        response = await client.post("/loans/", json=loan_payload)
        # Pode ser 201 (sucesso) ou 400 (se regra de negocio bloquear algo),
        # mas não 429
        assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS

    # 3. A 6ª deve ser bloqueada (429)
    response = await client.post("/loans/", json=loan_payload)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
