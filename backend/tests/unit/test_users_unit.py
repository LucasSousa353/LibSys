import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from app.api.v1.routers.users import create_user, get_user, list_users, list_user_loans
from app.domains.loans.models import Loan, LoanStatus
from app.domains.users.schemas import UserCreate
from app.domains.users.models import User


class TestUserFixtures:
    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.delete = AsyncMock()

        async def empty_scan_iter(match):
            return
            yield

        redis.scan_iter = empty_scan_iter
        return redis

    @pytest.fixture
    def mock_current_user(self):
        return User(
            id=1, name="Admin", email="admin@test.com", hashed_password="hashed"
        )

    @pytest.fixture
    def sample_user(self):
        return User(
            id=1,
            name="John Doe",
            email="john@example.com",
            hashed_password="hashed_password",
        )

    @pytest.fixture
    def sample_loan(self):
        now = datetime.now(timezone.utc)
        return Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=now,
            expected_return_date=now + timedelta(days=14),
            fine_amount=Decimal("0.00"),
            status=LoanStatus.ACTIVE,
        )

    @pytest.fixture
    def sample_user_create(self):
        return UserCreate(
            name="John Doe", email="john@example.com", password="securepassword123"
        )


class TestCreateUser(TestUserFixtures):
    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_db_session, sample_user_create):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with patch(
            "app.domains.users.services.get_password_hash", return_value="hashed"
        ):
            new_user = await create_user(sample_user_create, db=mock_db_session)

        assert new_user.email == "john@example.com"
        assert new_user.name == "John Doe"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email_raises_400(
        self, mock_db_session, sample_user_create, sample_user
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await create_user(sample_user_create, db=mock_db_session)

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email já registrado" in exc.value.detail
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_user_hashes_password(
        self, mock_db_session, sample_user_create
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with patch(
            "app.domains.users.services.get_password_hash",
            return_value="secure_hash_value",
        ) as mock_hash:
            new_user = await create_user(sample_user_create, db=mock_db_session)
            mock_hash.assert_called_once_with(sample_user_create.password)

        assert new_user.hashed_password == "secure_hash_value"

    @pytest.mark.asyncio
    async def test_create_user_with_different_emails(self, mock_db_session):
        emails = ["user1@test.com", "user.name@domain.org", "test+tag@example.co"]

        for email in emails:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute.return_value = mock_result
            mock_db_session.reset_mock()

            user_create = UserCreate(
                name="Test User", email=email, password="password123"
            )

            with patch(
                "app.domains.users.services.get_password_hash", return_value="hashed"
            ):
                new_user = await create_user(user_create, db=mock_db_session)

            assert new_user.email == email


class TestGetUser(TestUserFixtures):
    @pytest.mark.asyncio
    async def test_get_user_found(
        self, mock_db_session, mock_current_user, sample_user
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await get_user(
            user_id=1, current_user=mock_current_user, db=mock_db_session
        )

        assert result.id == 1
        assert result.name == "John Doe"
        assert result.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found_raises_404(
        self, mock_db_session, mock_current_user
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_user(
                user_id=999, current_user=mock_current_user, db=mock_db_session
            )

        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Usuário não localizado" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_user_with_negative_id_not_found(
        self, mock_db_session, mock_current_user
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_user(
                user_id=-1, current_user=mock_current_user, db=mock_db_session
            )

        assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_user_with_zero_id_not_found(
        self, mock_db_session, mock_current_user
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_user(
                user_id=0, current_user=mock_current_user, db=mock_db_session
            )

        assert exc.value.status_code == status.HTTP_404_NOT_FOUND


class TestListUsers(TestUserFixtures):
    @pytest.mark.asyncio
    async def test_list_users_returns_all(self, mock_db_session, mock_current_user):
        users = [
            User(id=1, name="User A", email="a@test.com", hashed_password="hash1"),
            User(id=2, name="User B", email="b@test.com", hashed_password="hash2"),
            User(id=3, name="User C", email="c@test.com", hashed_password="hash3"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = users
        mock_db_session.execute.return_value = mock_result

        result = await list_users(
            current_user=mock_current_user, skip=0, limit=10, db=mock_db_session
        )

        assert len(result) == 3
        assert result[0].name == "User A"
        assert result[1].name == "User B"
        assert result[2].name == "User C"

    @pytest.mark.asyncio
    async def test_list_users_empty_result(self, mock_db_session, mock_current_user):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await list_users(
            current_user=mock_current_user, skip=0, limit=10, db=mock_db_session
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_list_users_with_pagination_skip(
        self, mock_db_session, mock_current_user
    ):
        users = [User(id=11, name="User K", email="k@test.com", hashed_password="hash")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = users
        mock_db_session.execute.return_value = mock_result

        result = await list_users(
            current_user=mock_current_user, skip=10, limit=5, db=mock_db_session
        )

        assert len(result) == 1
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_users_with_limit(self, mock_db_session, mock_current_user):
        users = [
            User(
                id=i,
                name=f"User {i}",
                email=f"user{i}@test.com",
                hashed_password="hash",
            )
            for i in range(5)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = users
        mock_db_session.execute.return_value = mock_result

        result = await list_users(
            current_user=mock_current_user, skip=0, limit=5, db=mock_db_session
        )

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_users_single_result(
        self, mock_db_session, mock_current_user, sample_user
    ):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_user]
        mock_db_session.execute.return_value = mock_result

        result = await list_users(
            current_user=mock_current_user, skip=0, limit=10, db=mock_db_session
        )

        assert len(result) == 1
        assert result[0].email == "john@example.com"


class TestListUserLoans(TestUserFixtures):
    @pytest.mark.asyncio
    async def test_list_user_loans_success(
        self, mock_db_session, mock_redis, mock_current_user, sample_user, sample_loan
    ):
        with (
            patch(
                "app.api.v1.routers.users.UserService.get_user_by_id",
                new=AsyncMock(return_value=sample_user),
            ) as mock_get_user,
            patch(
                "app.api.v1.routers.users.LoanService.list_loans",
                new=AsyncMock(return_value=[sample_loan]),
            ) as mock_list_loans,
        ):
            result = await list_user_loans(
                user_id=1,
                current_user=mock_current_user,
                status=None,
                skip=0,
                limit=10,
                db=mock_db_session,
                redis=mock_redis,
            )

        assert len(result) == 1
        assert result[0].user_id == 1
        mock_get_user.assert_awaited_once_with(1)
        mock_list_loans.assert_awaited_once_with(
            user_id=1, status=None, skip=0, limit=10
        )

    @pytest.mark.asyncio
    async def test_list_user_loans_user_not_found_raises_404(
        self, mock_db_session, mock_redis, mock_current_user
    ):
        with patch(
            "app.api.v1.routers.users.UserService.get_user_by_id",
            new=AsyncMock(side_effect=LookupError("Usuário não localizado")),
        ):
            with pytest.raises(HTTPException) as exc:
                await list_user_loans(
                    user_id=999,
                    current_user=mock_current_user,
                    status=None,
                    skip=0,
                    limit=10,
                    db=mock_db_session,
                    redis=mock_redis,
                )

        assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_user_loans_status_filter(
        self, mock_db_session, mock_redis, mock_current_user, sample_user
    ):
        with (
            patch(
                "app.api.v1.routers.users.UserService.get_user_by_id",
                new=AsyncMock(return_value=sample_user),
            ) as mock_get_user,
            patch(
                "app.api.v1.routers.users.LoanService.list_loans",
                new=AsyncMock(return_value=[]),
            ) as mock_list_loans,
        ):
            result = await list_user_loans(
                user_id=1,
                current_user=mock_current_user,
                status=LoanStatus.RETURNED,
                skip=5,
                limit=3,
                db=mock_db_session,
                redis=mock_redis,
            )

        assert result == []
        mock_get_user.assert_awaited_once_with(1)
        mock_list_loans.assert_awaited_once_with(
            user_id=1, status=LoanStatus.RETURNED, skip=5, limit=3
        )
