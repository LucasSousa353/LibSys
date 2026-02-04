import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_full_loan_cycle(client):
    # 1. Criar Usuário
    user_payload = {"name": "Test User", "email": "test@libsys.com"}
    response = await client.post("/users/", json=user_payload)
    assert response.status_code == status.HTTP_201_CREATED
    user_id = response.json()["id"]

    # 2. Criar Livro (Total copies: 2)
    book_payload = {
        "title": "Arquitetura Limpa",
        "author": "Uncle Bob",
        "isbn": "978-8550804606",
        "total_copies": 2
    }
    response = await client.post("/books/", json=book_payload)
    assert response.status_code == status.HTTP_201_CREATED
    book_id = response.json()["id"]

    # 3. Empréstimo 1 (OK)
    loan_payload = {"user_id": user_id, "book_id": book_id}
    response = await client.post("/loans/", json=loan_payload)
    assert response.status_code == status.HTTP_201_CREATED
    loan1_id = response.json()["id"]
    
    # Verifica estoque (deve ser 1)
    response = await client.get(f"/books/{book_id}")
    assert response.json()["available_copies"] == 1

    # 4. Empréstimo 2 (OK - Pega a última cópia)
    response = await client.post("/loans/", json=loan_payload)
    assert response.status_code == status.HTTP_201_CREATED
    loan2_id = response.json()["id"]

    # Verifica estoque (deve ser 0)
    response = await client.get(f"/books/{book_id}")
    assert response.json()["available_copies"] == 0

    # 5. Empréstimo 3 (Falha - Sem estoque)
    response = await client.post("/loans/", json=loan_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Livro não disponível no estoque"

    # 6. Devolver Empréstimo 1
    response = await client.post(f"/loans/{loan1_id}/return")
    assert response.status_code == status.HTTP_200_OK
    
    # Verifica estoque (deve voltar para 1)
    response = await client.get(f"/books/{book_id}")
    assert response.json()["available_copies"] == 1

    # 7. Empréstimo 3 (Agora deve funcionar)
    response = await client.post("/loans/", json=loan_payload)
    assert response.status_code == status.HTTP_201_CREATED
    
    # 8. Verificar histórico do usuário
    response = await client.get(f"/loans/?user_id={user_id}")
    loans = response.json()
    assert len(loans) == 3 # 2 Ativos + 1 Devolvido