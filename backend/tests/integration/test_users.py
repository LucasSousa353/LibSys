import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_create_user_success(client):
    payload = {"name": "Test User", "email": "test@user.com", "password": "pass123"}
    response = await client.post("/users/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == payload["email"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client):
    payload = {"name": "Ref User", "email": "dup@user.com", "password": "pass123"}
    await client.post("/users/", json=payload)

    response = await client.post("/users/", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email já registrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user_by_id(client):
    # Create
    create_resp = await client.post(
        "/users/",
        json={"name": "FindMe", "email": "find@me.com", "password": "pass123"},
    )
    user_id = create_resp.json()["id"]

    # Get
    get_resp = await client.get(f"/users/{user_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["name"] == "FindMe"


@pytest.mark.asyncio
async def test_get_user_not_found(client):
    response = await client.get("/users/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
