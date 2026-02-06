import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
import jwt

from app.domains.auth.dependencies import get_current_user
from app.domains.users.models import User

TEST_SECRET_KEY = "test_secret_key_with_minimum_32_bytes_for_hs256"
WRONG_SECRET_KEY = "wrong_secret_key_with_minimum_32_bytes"


class TestGetCurrentUser:
    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

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
        self, mock_settings, mock_db_session, sample_user
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode(
            {"sub": "test@example.com"}, TEST_SECRET_KEY, algorithm="HS256"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        user = await get_current_user(token=token, db=mock_db_session)

        assert user.email == "test@example.com"
        assert user.id == 1

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_invalid_token_raises_401(
        self, mock_settings, mock_db_session
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=mock_db_session)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Credenciais inválidas" in exc.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_token_wrong_secret_raises_401(
        self, mock_settings, mock_db_session
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode(
            {"sub": "test@example.com"}, WRONG_SECRET_KEY, algorithm="HS256"
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=mock_db_session)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_token_missing_sub_raises_401(
        self, mock_settings, mock_db_session
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode({"user_id": 123}, TEST_SECRET_KEY, algorithm="HS256")

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=mock_db_session)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_user_not_found_raises_401(
        self, mock_settings, mock_db_session
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode(
            {"sub": "nonexistent@example.com"}, TEST_SECRET_KEY, algorithm="HS256"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=mock_db_session)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_inactive_user_raises_403(
        self, mock_settings, mock_db_session, sample_user
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

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=mock_db_session)

        assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_expired_token_raises_401(
        self, mock_settings, mock_db_session
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

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=mock_db_session)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_empty_token_raises_401(
        self, mock_settings, mock_db_session
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token="", db=mock_db_session)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_includes_www_authenticate_header(
        self, mock_settings, mock_db_session
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = "invalid.token"

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=mock_db_session)

        assert exc.value.headers is not None
        assert exc.value.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.settings")
    async def test_get_current_user_token_with_none_sub_raises_401(
        self, mock_settings, mock_db_session
    ):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"

        token = jwt.encode({"sub": None}, TEST_SECRET_KEY, algorithm="HS256")

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=mock_db_session)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
