from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.messages import ErrorMessages
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserRole
from app.domains.users.services import UserService


class TestUserServiceFixtures:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        service = UserService(db=mock_db)
        service.repository = MagicMock()
        service.repository.find_by_email = AsyncMock()
        service.repository.find_by_id = AsyncMock()
        service.repository.find_all = AsyncMock()
        service.repository.find_lookup = AsyncMock()
        service.repository.find_by_ids = AsyncMock()
        service.repository.create = AsyncMock()
        service.repository.update = AsyncMock()
        return service

    @pytest.fixture
    def sample_user(self):
        return User(
            id=1,
            name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role=UserRole.USER.value,
            must_reset_password=False,
            is_active=True,
        )


class TestCreateUser(TestUserServiceFixtures):
    @pytest.mark.asyncio
    async def test_create_user_success(self, service, mock_db):
        service.repository.find_by_email.return_value = None
        user_model = User(
            id=1,
            name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role=UserRole.USER.value,
            must_reset_password=False,
            is_active=True,
        )
        service.repository.create.return_value = user_model

        with (
            patch(
                "app.domains.users.services.get_password_hash", return_value="hashed"
            ),
            patch(
                "app.domains.users.services.AuditLogService.log_event", new=AsyncMock()
            ),
        ):
            user = await service.create_user(
                UserCreate(
                    name="John Doe", email="john@example.com", password="pass123"
                )
            )

        assert user.email == "john@example.com"
        assert user.role == UserRole.USER.value
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, service, sample_user):
        service.repository.find_by_email.return_value = sample_user

        with pytest.raises(ValueError) as exc:
            await service.create_user(
                UserCreate(
                    name="John Doe", email="john@example.com", password="pass123"
                )
            )

        assert ErrorMessages.USER_EMAIL_ALREADY_EXISTS in str(exc.value)


class TestUpdateUserStatus(TestUserServiceFixtures):
    @pytest.mark.asyncio
    async def test_update_user_status(self, service, mock_db, sample_user):
        service.repository.find_by_id.return_value = sample_user

        with patch(
            "app.domains.users.services.AuditLogService.log_event", new=AsyncMock()
        ):
            updated = await service.update_user_status(sample_user.id, False)

        assert updated.is_active is False
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


class TestPasswordReset(TestUserServiceFixtures):
    @pytest.mark.asyncio
    async def test_require_password_reset(self, service, mock_db, sample_user):
        service.repository.find_by_id.return_value = sample_user

        with patch(
            "app.domains.users.services.AuditLogService.log_event", new=AsyncMock()
        ):
            updated = await service.require_password_reset(sample_user.id)

        assert updated.must_reset_password is True
        assert updated.password_reset_at is not None
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reset_password(self, service, mock_db, sample_user):
        service.repository.find_by_id.return_value = sample_user

        with (
            patch(
                "app.domains.users.services.get_password_hash", return_value="new_hash"
            ),
            patch(
                "app.domains.users.services.AuditLogService.log_event", new=AsyncMock()
            ),
            patch("app.domains.auth.security.verify_password", return_value=True),
        ):
            updated = await service.reset_password(
                sample_user.id, "newpass123", current_password="oldpass"
            )

        assert updated.must_reset_password is False
        assert updated.password_reset_at is not None
        assert updated.hashed_password == "new_hash"
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reset_password_wrong_current_password_raises(
        self, service, mock_db, sample_user
    ):
        service.repository.find_by_id.return_value = sample_user

        with (
            patch("app.domains.auth.security.verify_password", return_value=False),
        ):
            with pytest.raises(ValueError, match="Senha atual incorreta"):
                await service.reset_password(
                    sample_user.id, "newpass123", current_password="wrongpass"
                )

    @pytest.mark.asyncio
    async def test_reset_password_same_as_current_raises(
        self, service, mock_db, sample_user
    ):
        service.repository.find_by_id.return_value = sample_user

        with (
            patch("app.domains.auth.security.verify_password", return_value=True),
        ):
            with pytest.raises(ValueError, match="nova senha não pode ser igual"):
                await service.reset_password(
                    sample_user.id, "samepass", current_password="samepass"
                )


class TestUserQueries(TestUserServiceFixtures):
    @pytest.mark.asyncio
    async def test_list_users(self, service, sample_user):
        service.repository.find_all.return_value = [sample_user]

        users = await service.list_users(skip=0, limit=10)

        assert len(users) == 1

    @pytest.mark.asyncio
    async def test_lookup_users(self, service, sample_user):
        service.repository.find_lookup.return_value = [sample_user]

        users = await service.lookup_users("john", skip=0, limit=10)

        assert len(users) == 1

    @pytest.mark.asyncio
    async def test_lookup_users_by_ids(self, service, sample_user):
        service.repository.find_by_ids.return_value = [sample_user]

        users = await service.lookup_users_by_ids([sample_user.id])

        assert len(users) == 1

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, service):
        service.repository.find_by_id.return_value = None

        with pytest.raises(LookupError) as exc:
            await service.get_user_by_id(999)

        assert ErrorMessages.USER_NOT_FOUND in str(exc.value)
