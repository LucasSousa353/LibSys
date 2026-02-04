import pytest
from datetime import datetime, timedelta, timezone
from fastapi import status
from app.loans.models import Loan, LoanStatus


@pytest.mark.asyncio
async def test_loan_lifecycle_success(client):
    """
    Testa o ciclo de vida completo: Empréstimo -> Devolução
    """
    # Setup
    u_resp = await client.post(
        "/users/", json={"name": "Lifecycle", "email": "life@cycle.com"}
    )
    user_id = u_resp.json()["id"]

    b_resp = await client.post(
        "/books/",
        json={"title": "Life Book", "author": "A", "isbn": "LF-1", "total_copies": 2},
    )
    book_id = b_resp.json()["id"]

    # 1. Realizar Empréstimo
    loan_resp = await client.post(
        "/loans/", json={"user_id": user_id, "book_id": book_id}
    )
    assert loan_resp.status_code == status.HTTP_201_CREATED
    loan_id = loan_resp.json()["id"]

    # Verificar status inicial
    assert loan_resp.json()["status"] == LoanStatus.ACTIVE

    # Verificar decremento de estoque
    book_check = await client.get(f"/books/{book_id}")
    assert book_check.json()["available_copies"] == 1

    # 2. Devolver Livro
    ret_resp = await client.post(f"/loans/{loan_id}/return")
    assert ret_resp.status_code == status.HTTP_200_OK
    assert ret_resp.json()["message"] == "Livro retornado."

    # Verificar se realmente mudou status (via listagem)
    list_active = await client.get(f"/loans/?user_id={user_id}&status=active")
    assert len(list_active.json()) == 0

    list_returned = await client.get(f"/loans/?user_id={user_id}&status=returned")
    assert len(list_returned.json()) == 1
    assert list_returned.json()[0]["id"] == loan_id

    # Verificar incremento de estoque
    book_check_2 = await client.get(f"/books/{book_id}")
    assert book_check_2.json()["available_copies"] == 2


@pytest.mark.asyncio
async def test_loan_out_of_stock(client):
    # Setup: 1 cópia
    u_resp = await client.post(
        "/users/", json={"name": "Stock", "email": "stock@u.com"}
    )
    user_id = u_resp.json()["id"]
    b_resp = await client.post(
        "/books/",
        json={"title": "Rare Book", "author": "A", "isbn": "RARE-1", "total_copies": 1},
    )
    book_id = b_resp.json()["id"]

    # Primeiro user pega
    await client.post("/loans/", json={"user_id": user_id, "book_id": book_id})

    # Segundo tenta pegar
    fail_resp = await client.post(
        "/loans/", json={"user_id": user_id, "book_id": book_id}
    )
    assert fail_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Livro não disponível no estoque" in fail_resp.json()["detail"]


@pytest.mark.asyncio
async def test_block_loan_if_overdue(client, db_session):
    """
    RN05: Bloqueia novo empréstimo se usuario tem atraso.
    Injeta dados diretamente no banco para simular data passada.
    """
    # Setup
    u_resp = await client.post(
        "/users/", json={"name": "Late User", "email": "late@user.com"}
    )
    user_id = u_resp.json()["id"]

    b1 = await client.post(
        "/books/",
        json={"title": "Old Book", "author": "A", "isbn": "OLD-1", "total_copies": 5},
    )
    book_id_1 = b1.json()["id"]

    b2 = await client.post(
        "/books/",
        json={"title": "New Book", "author": "B", "isbn": "NEW-1", "total_copies": 5},
    )
    book_id_2 = b2.json()["id"]

    # Criar empréstimo atrasado manualmente
    past_date = datetime.now(timezone.utc) - timedelta(days=30)
    expected_return = past_date + timedelta(days=14)  # Venceu há 16 dias

    bad_loan = Loan(
        user_id=user_id,
        book_id=book_id_1,
        loan_date=past_date,
        expected_return_date=expected_return,
        status=LoanStatus.ACTIVE,
    )
    db_session.add(bad_loan)
    await db_session.commit()

    # Tentar novo empréstimo
    resp = await client.post("/loans/", json={"user_id": user_id, "book_id": book_id_2})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "atrasados pendentes" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_filter_loans(client):
    u_resp = await client.post(
        "/users/", json={"name": "Filter User", "email": "filter@u.com"}
    )
    user_id = u_resp.json()["id"]
    b_resp = await client.post(
        "/books/",
        json={"title": "F Book", "author": "F", "isbn": "F-1", "total_copies": 5},
    )
    book_id = b_resp.json()["id"]

    # Cria empréstimo
    await client.post("/loans/", json={"user_id": user_id, "book_id": book_id})

    # Busca Active - Usando .value para o Enum
    resp = await client.get(
        f"/loans/?status={LoanStatus.ACTIVE.value}&user_id={user_id}"
    )
    assert len(resp.json()) == 1

    # Busca Returned (0) - Usando .value para o Enum
    resp = await client.get(
        f"/loans/?status={LoanStatus.RETURNED.value}&user_id={user_id}"
    )
    assert len(resp.json()) == 0
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_return_already_returned_loan(client):
    u_resp = await client.post("/users/", json={"name": "Ret", "email": "ret@u.com"})
    user_id = u_resp.json()["id"]
    b_resp = await client.post(
        "/books/",
        json={"title": "R Book", "author": "R", "isbn": "R-1", "total_copies": 5},
    )
    book_id = b_resp.json()["id"]

    loan_resp = await client.post(
        "/loans/", json={"user_id": user_id, "book_id": book_id}
    )
    loan_id = loan_resp.json()["id"]

    # 1. Devolve
    await client.post(f"/loans/{loan_id}/return")

    # 2. Devolve de novo
    resp = await client.post(f"/loans/{loan_id}/return")
    # Geralmente deve falhar pois não está ACTIVE
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Empréstimo já devolvido" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_user_not_found_create_loan(client):
    b_resp = await client.post(
        "/books/",
        json={"title": "Ghost", "author": "G", "isbn": "G-1", "total_copies": 1},
    )
    book_id = b_resp.json()["id"]

    resp = await client.post("/loans/", json={"user_id": 99999, "book_id": book_id})
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_max_active_loans_limit(client):
    """
    RN: Usuário só pode ter até 3 empréstimos ativos.
    """
    # Setup
    u_resp = await client.post(
        "/users/", json={"name": "Max Loans", "email": "max@loans.com"}
    )
    user_id = u_resp.json()["id"]

    # Cria 4 livros
    books = []
    for i in range(4):
        resp = await client.post(
            "/books/",
            json={
                "title": f"B{i}",
                "author": "A",
                "isbn": f"MAX-{i}",
                "total_copies": 5,
            },
        )
        books.append(resp.json()["id"])

    # Pega 3 empréstimos (Limite)
    for i in range(3):
        resp = await client.post(
            "/loans/", json={"user_id": user_id, "book_id": books[i]}
        )
        assert resp.status_code == status.HTTP_201_CREATED

    # Tenta o 4º
    resp = await client.post("/loans/", json={"user_id": user_id, "book_id": books[3]})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "atingiu o limite" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_loan_book_not_found(client):
    u_resp = await client.post(
        "/users/", json={"name": "NoBook", "email": "no@book.com"}
    )
    user_id = u_resp.json()["id"]

    resp = await client.post("/loans/", json={"user_id": user_id, "book_id": 99999})
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert "Livro não encontrado" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_return_loan_not_found(client):
    resp = await client.post("/loans/99999/return")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert "Empréstimo não encontrado" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_return_loan_with_fine(client, db_session):
    """
    Simula devolução atrasada para verificar cálculo de multa.
    """
    # Setup
    u_resp = await client.post(
        "/users/", json={"name": "Fine User", "email": "fine@user.com"}
    )
    user_id = u_resp.json()["id"]
    b_resp = await client.post(
        "/books/",
        json={"title": "Fine Book", "author": "A", "isbn": "FINE-1", "total_copies": 5},
    )
    book_id = b_resp.json()["id"]

    # Criar empréstimo atrasado manualmente (5 dias atraso)
    # expected_return foi há 5 dias
    now = datetime.now(timezone.utc)
    expected = now - timedelta(days=5)
    loan_date = expected - timedelta(days=14)

    loan = Loan(
        user_id=user_id,
        book_id=book_id,
        loan_date=loan_date,
        expected_return_date=expected,
        status=LoanStatus.ACTIVE,
    )
    db_session.add(loan)
    await db_session.commit()
    await db_session.refresh(loan)

    # Devolver
    resp = await client.post(f"/loans/{loan.id}/return")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    # 5 dias * 2.00 = 10.00
    assert data["days_overdue"] == 5
    assert data["fine_amount"] == "R$ 10.00"
