from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
import jwt

from app.domains.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)

TEST_SECRET_KEY = "test_secret_key_with_minimum_32_bytes_for_hs256"


class TestPasswordHashing:
    def test_get_password_hash_returns_hashed_string(self):
        password = "mysecretpassword"

        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_get_password_hash_different_for_same_password(self):
        password = "samepassword"

        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2

    def test_verify_password_correct_password_returns_true(self):
        password = "correctpassword"
        hashed = get_password_hash(password)

        result = verify_password(password, hashed)

        assert result is True

    def test_verify_password_wrong_password_returns_false(self):
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        result = verify_password(wrong_password, hashed)

        assert result is False

    def test_verify_password_empty_password_returns_false(self):
        password = "somepassword"
        hashed = get_password_hash(password)

        result = verify_password("", hashed)

        assert result is False

    def test_get_password_hash_handles_unicode(self):
        password = "senhaçãoéê123"

        hashed = get_password_hash(password)
        result = verify_password(password, hashed)

        assert result is True

    def test_get_password_hash_handles_long_password(self):
        password = "a" * 200

        hashed = get_password_hash(password)
        result = verify_password(password, hashed)

        assert result is True

    def test_verify_password_case_sensitive(self):
        password = "Password123"
        hashed = get_password_hash(password)

        result_lower = verify_password("password123", hashed)
        result_upper = verify_password("PASSWORD123", hashed)

        assert result_lower is False
        assert result_upper is False


class TestAccessToken:
    @patch("app.domains.auth.security.settings")
    def test_create_access_token_returns_valid_jwt(self, mock_settings):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "test@example.com"}

        token = create_access_token(data)

        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])
        assert decoded["sub"] == "test@example.com"

    @patch("app.domains.auth.security.settings")
    def test_create_access_token_includes_expiration(self, mock_settings):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "test@example.com"}

        token = create_access_token(data)

        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])
        assert "exp" in decoded

    @patch("app.domains.auth.security.settings")
    def test_create_access_token_with_custom_expiration(self, mock_settings):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(hours=2)

        token = create_access_token(data, expires_delta=expires_delta)

        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + expires_delta
        assert abs((exp_time - expected_time).total_seconds()) < 5

    @patch("app.domains.auth.security.settings")
    def test_create_access_token_default_expiration_15_minutes(self, mock_settings):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "test@example.com"}

        token = create_access_token(data)

        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        assert abs((exp_time - expected_time).total_seconds()) < 5

    @patch("app.domains.auth.security.settings")
    def test_create_access_token_preserves_additional_data(self, mock_settings):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "test@example.com", "role": "admin", "user_id": 123}

        token = create_access_token(data)

        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])
        assert decoded["sub"] == "test@example.com"
        assert decoded["role"] == "admin"
        assert decoded["user_id"] == 123

    @patch("app.domains.auth.security.settings")
    def test_create_access_token_does_not_modify_original_data(self, mock_settings):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "test@example.com"}
        original_data = data.copy()

        create_access_token(data)

        assert data == original_data
        assert "exp" not in data

    @patch("app.domains.auth.security.settings")
    def test_create_access_token_with_very_short_expiration(self, mock_settings):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(seconds=1)

        token = create_access_token(data, expires_delta=expires_delta)

        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])
        assert "exp" in decoded

    @patch("app.domains.auth.security.settings")
    def test_create_access_token_with_very_long_expiration(self, mock_settings):
        mock_settings.SECRET_KEY = TEST_SECRET_KEY
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(days=365)

        token = create_access_token(data, expires_delta=expires_delta)

        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + expires_delta
        assert abs((exp_time - expected_time).total_seconds()) < 5
