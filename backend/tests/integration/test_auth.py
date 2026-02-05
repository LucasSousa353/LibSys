import base64
import json
from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.domains.auth.security import create_access_token, get_password_hash
from tests.factories import UserFactory


TEST_PASSWORD = "correctpassword123"


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Email ou senha incorretos" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client_unauthenticated: AsyncClient):
        response = await client_unauthenticated.post(
            "/token",
            data={"username": "nonexistent@example.com", "password": "anypassword"},
        )
        assert response.status_code == 401
        assert "Email ou senha incorretos" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_missing_username(self, client_unauthenticated: AsyncClient):
        response = await client_unauthenticated.post(
            "/token", data={"password": "somepassword"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_password(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, client_unauthenticated: AsyncClient):
        response = await client_unauthenticated.post(
            "/token", data={"username": "", "password": ""}
        )
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_login_case_sensitive_email(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email.upper(), "password": TEST_PASSWORD}
        )
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_login_returns_valid_jwt(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        assert len(token.split(".")) == 3


class TestAuthenticatedEndpoints:
    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_valid_token(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        login_response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        token = login_response.json()["access_token"]
        response = await client_unauthenticated.get(
            "/users/", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_without_token(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get("/users/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_invalid_token(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get(
            "/users/", headers={"Authorization": "Bearer invalidtoken123"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_malformed_header(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get(
            "/users/", headers={"Authorization": "NotBearer token123"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_expired_token(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        expired_token = create_access_token(
            data={"sub": user.email}, expires_delta=timedelta(seconds=-1)
        )
        response = await client_unauthenticated.get(
            "/users/", headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401


class TestTokenPayload:
    def _decode_jwt_payload(self, token: str) -> dict:
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload_b64))

    @pytest.mark.asyncio
    async def test_token_contains_user_email(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        payload = self._decode_jwt_payload(token)
        assert payload["sub"] == user.email

    @pytest.mark.asyncio
    async def test_token_contains_expiration(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(hashed_password=get_password_hash(TEST_PASSWORD))
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        payload = self._decode_jwt_payload(token)
        assert "exp" in payload
