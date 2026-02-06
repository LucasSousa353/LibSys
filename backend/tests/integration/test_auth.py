import base64
import json
from datetime import timedelta

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis

from app.domains.auth.security import create_access_token, get_password_hash
from app.domains.users.schemas import UserRole


TEST_PASSWORD = "correctpassword123"


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == UserRole.ADMIN.value
        assert data["must_reset_password"] is False

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
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
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
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
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email.upper(), "password": TEST_PASSWORD}
        )
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_login_returns_valid_jwt(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        assert len(token.split(".")) == 3

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
            is_active=False,
        )
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 403
        assert "Usuário inativo" in response.json()["detail"]


class TestAuthenticatedEndpoints:
    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_valid_token(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
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
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
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
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
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
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        payload = self._decode_jwt_payload(token)
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_token_contains_role(
        self, client_unauthenticated: AsyncClient, create_user
    ):
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        payload = self._decode_jwt_payload(token)
        assert payload["role"] == UserRole.ADMIN.value


class TestLoginLockout:
    """Tests for brute-force protection on /token."""

    @pytest.mark.asyncio
    async def test_account_locks_after_max_failed_attempts(
        self, client_unauthenticated: AsyncClient, create_user, redis_client_test: Redis
    ):
        """After LOGIN_MAX_ATTEMPTS failures the account must be locked (429)."""
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        # Exhaust attempts (default 5)
        for _ in range(5):
            await client_unauthenticated.post(
                "/token", data={"username": user.email, "password": "wrong"}
            )

        # Next attempt should be locked
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": "wrong"}
        )
        assert response.status_code == 429
        assert "bloqueada" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_lockout_blocks_even_correct_password(
        self, client_unauthenticated: AsyncClient, create_user, redis_client_test: Redis
    ):
        """Even the correct password must be rejected while the account is locked."""
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        for _ in range(5):
            await client_unauthenticated.post(
                "/token", data={"username": user.email, "password": "wrong"}
            )

        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_successful_login_resets_attempt_counter(
        self, client_unauthenticated: AsyncClient, create_user, redis_client_test: Redis
    ):
        """A successful login must clear the failed-attempt counter."""
        user = await create_user(
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        # 4 failures (just below the limit)
        for _ in range(4):
            await client_unauthenticated.post(
                "/token", data={"username": user.email, "password": "wrong"}
            )

        # Correct password resets the counter
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200

        # Should be able to fail again without immediate lockout
        response = await client_unauthenticated.post(
            "/token", data={"username": user.email, "password": "wrong"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_lockout_does_not_affect_other_users(
        self, client_unauthenticated: AsyncClient, create_user, redis_client_test: Redis
    ):

        user_a = await create_user(
            email="lockeduser@test.com",
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )
        user_b = await create_user(
            email="freeuser@test.com",
            hashed_password=get_password_hash(TEST_PASSWORD),
            role=UserRole.ADMIN.value,
        )

        for _ in range(5):
            await client_unauthenticated.post(
                "/token", data={"username": user_a.email, "password": "wrong"}
            )

        # user_b must still be able to login
        response = await client_unauthenticated.post(
            "/token", data={"username": user_b.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
