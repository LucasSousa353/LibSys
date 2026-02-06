import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
import jwt

from app.domains.auth.dependencies import get_current_user
from app.domains.users.models import User

TEST_SECRET_KEY = "test_secret_key_with_minimum_32_bytes_for_hs256"
WRONG_SECRET_KEY = "wrong_secret_key_with_minimum_32_bytes"


def _make_mock_request(path: str = "/users/me") -> MagicMock:
    """Helper to create a mock Request with the given URL path."""
    request = MagicMock()
    url = MagicMock()
    url.path = path
    request.url = url
    return request


class TestGetCurrentUser:
    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.exists = AsyncMock(return_value=0)
        return redis

    @pytest.fixture
    def sample_user(self):
        return User(
            id=1,
            name="Test User",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_valid_token(
        self, mock_settings, mock_db_session, mock_redis, sample_user
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode(
            {"sub": "test@example.com"}, TEST_SECRET_KEY, algorithm="HS256"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        request = _make_mock_request()
        user = await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert user.email == "test@example.com"
        assert user.id == 1

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_invalid_token_raises_401(
        self, mock_settings, mock_db_session, mock_redis
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = "invalid.token.here"

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Credenciais inválidas" in exc.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_token_wrong_secret_raises_401(
        self, mock_settings, mock_db_session, mock_redis
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode(
            {"sub": "test@example.com"}, WRONG_SECRET_KEY, algorithm="HS256"
        )

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_token_missing_sub_raises_401(
        self, mock_settings, mock_db_session, mock_redis
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode({"user_id": 123}, TEST_SECRET_KEY, algorithm="HS256")

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_user_not_found_raises_401(
        self, mock_settings, mock_db_session, mock_redis
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode(
            {"sub": "nonexistent@example.com"}, TEST_SECRET_KEY, algorithm="HS256"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_inactive_user_raises_403(
        self, mock_settings, mock_db_session, mock_redis, sample_user
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        sample_user.is_active = False

        token = jwt.encode(
            {"sub": "test@example.com"}, TEST_SECRET_KEY, algorithm="HS256"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_expired_token_raises_401(
        self, mock_settings, mock_db_session, mock_redis
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        from datetime import datetime, timedelta, timezone

        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        token = jwt.encode(
            {"sub": "test@example.com", "exp": expired_time},
            TEST_SECRET_KEY,
            algorithm="HS256",
        )

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_empty_token_raises_401(
        self, mock_settings, mock_db_session, mock_redis
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token="", db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_includes_www_authenticate_header(
        self, mock_settings, mock_db_session, mock_redis
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = "invalid.token"

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.headers is not None
        assert exc.value.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_token_with_none_sub_raises_401(
        self, mock_settings, mock_db_session, mock_redis
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode({"sub": None}, TEST_SECRET_KEY, algorithm="HS256")

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_token_issued_before_password_reset_raises_401(
        self, mock_settings, mock_db_session, mock_redis, sample_user
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        iat = datetime.now(timezone.utc) - timedelta(hours=1)
        token = jwt.encode(
            {"sub": "test@example.com", "iat": iat},
            TEST_SECRET_KEY,
            algorithm="HS256",
        )

        sample_user.password_reset_at = datetime.now(timezone.utc) - timedelta(
            minutes=30
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_token_issued_after_password_reset_succeeds(
        self, mock_settings, mock_db_session, mock_redis, sample_user
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        sample_user.password_reset_at = datetime.now(timezone.utc) - timedelta(hours=1)

        iat = datetime.now(timezone.utc) - timedelta(minutes=30)
        token = jwt.encode(
            {"sub": "test@example.com", "iat": iat},
            TEST_SECRET_KEY,
            algorithm="HS256",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        request = _make_mock_request()
        user = await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_must_reset_password_blocks_regular_routes(
        self, mock_settings, mock_db_session, mock_redis, sample_user
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        sample_user.must_reset_password = True

        token = jwt.encode(
            {"sub": "test@example.com"},
            TEST_SECRET_KEY,
            algorithm="HS256",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        request = _make_mock_request("/books")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert exc.value.status_code == status.HTTP_403_FORBIDDEN
        assert "redefinir a senha" in exc.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_must_reset_password_allows_reset_endpoint(
        self, mock_settings, mock_db_session, mock_redis, sample_user
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        sample_user.must_reset_password = True

        token = jwt.encode(
            {"sub": "test@example.com"},
            TEST_SECRET_KEY,
            algorithm="HS256",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        request = _make_mock_request("/users/me/reset-password")
        user = await get_current_user(request=request, token=token, db=mock_db_session, redis=mock_redis)

        assert user.email == "test@example.com"
