import pytest
from datetime import datetime, timedelta, timezone
from fastapi import status
from app.models.loan import Loan, LoanStatus


@pytest.mark.asyncio
async def test_block_loan_if_overdue(client, db_session):
    """
    RN05: Testa se o sistema bloqueia novo empréstimo
    se o usuário tiver um livro atrasado (mesmo que ACTIVE).
    """
    # 1. Setup: Criar User e Livros via API para garantir integridade
    u_resp = await client.post(
        "/users/", json={"name": "User", "email": "user@user.com"}
    )
    user_id = u_resp.json()["id"]

    b_resp = await client.post(
        "/books/",
        json={"title": "Livro A", "author": "A", "isbn": "001", "total_copies": 5},
    )
    book_id_A = b_resp.json()["id"]

    b_resp2 = await client.post(
        "/books/",
        json={"title": "Livro B", "author": "B", "isbn": "002", "total_copies": 5},
    )
    book_id_B = b_resp2.json()["id"]

    # 2. Setup do Cenário de Atraso (Usando ORM)
    past_date = datetime.now(timezone.utc) - timedelta(days=20)
    expected_date = past_date + timedelta(days=14)

    bad_loan = Loan(
        user_id=user_id,
        book_id=book_id_A,
        loan_date=past_date,
        expected_return_date=expected_date,
        status=LoanStatus.ACTIVE,
    )
    db_session.add(bad_loan)
    await db_session.commit()

    # 3. Tentar alugar o Livro B (Deve ser bloqueado)
    response = await client.post(
        "/loans/", json={"user_id": user_id, "book_id": book_id_B}
    )

    if response.status_code != status.HTTP_400_BAD_REQUEST:
        print(f"DEBUG RESPONSE: {response.json()}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "atrasados pendentes" in response.json()["detail"]


@pytest.mark.asyncio
async def test_filter_loans_by_status(client, db_session):
    """
    RF11: Testa filtro de status na listagem.
    """
    u_resp = await client.post(
        "/users/", json={"name": "Filter User", "email": "filter@user.com"}
    )
    user_id = u_resp.json()["id"]
    b_resp = await client.post(
        "/books/",
        json={"title": "Livro F", "author": "F", "isbn": "999", "total_copies": 5},
    )
    book_id = b_resp.json()["id"]

    loan_resp = await client.post(
        "/loans/", json={"user_id": user_id, "book_id": book_id}
    )
    loan_id = loan_resp.json()["id"]

    # 1. Buscar apenas ACTIVE
    resp_active = await client.get(f"/loans/?status=active&user_id={user_id}")
    assert len(resp_active.json()) == 1

    # 2. Buscar apenas RETURNED (Deve vir vazio)
    resp_returned = await client.get(f"/loans/?status=returned&user_id={user_id}")
    assert len(resp_returned.json()) == 0

    # 3. Devolver
    await client.post(f"/loans/{loan_id}/return")

    # 4. Buscar apenas RETURNED (Deve achar agora)
    resp_returned_after = await client.get(f"/loans/?status=returned&user_id={user_id}")
    assert len(resp_returned_after.json()) == 1
