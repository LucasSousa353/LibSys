from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.core.messages import ErrorMessages
from app.domains.books.models import Book
from app.domains.loans.models import Loan, LoanStatus
from app.domains.loans.schemas import LoanCreate
from app.domains.loans.services import LoanService
from app.domains.users.models import User


class TestLoanServiceFixtures:
    @pytest.fixture
    def fixed_now(self):
        return datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.flush = AsyncMock()
        return db

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
    def loan_service(self, mock_db, mock_redis, fixed_now):
        service = LoanService(mock_db, mock_redis, get_now_fn=lambda: fixed_now)
        service.loan_repository = MagicMock()
        service.book_repository = MagicMock()
        service.user_repository = MagicMock()
        service.loan_repository.create = AsyncMock()
        service.loan_repository.update = AsyncMock()
        service.loan_repository.count_active_loans_by_user = AsyncMock()
        service.loan_repository.find_overdue_loans_by_user = AsyncMock()
        service.loan_repository.find_all = AsyncMock()
        service.loan_repository.find_all_with_relations = AsyncMock()
        service.loan_repository.find_by_id_with_lock = AsyncMock()
        service.book_repository.find_by_id_with_lock = AsyncMock()
        service.book_repository.update = AsyncMock()
        service.user_repository.find_by_id = AsyncMock()
        return service

    @pytest.fixture
    def sample_book(self):
        return Book(
            id=1,
            title="Test Book",
            author="Author",
            isbn="TEST-001",
            total_copies=5,
            available_copies=3,
        )

    @pytest.fixture
    def sample_book_no_copies(self):
        return Book(
            id=2,
            title="Popular Book",
            author="Author",
            isbn="POP-001",
            total_copies=5,
            available_copies=0,
        )

    @pytest.fixture
    def sample_user(self):
        return User(
            id=1, name="Test User", email="test@test.com", hashed_password="hash"
        )

    @pytest.fixture
    def sample_loan_create(self):
        return LoanCreate(user_id=1, book_id=1)

    @pytest.fixture
    def sample_active_loan(self, fixed_now):
        return Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=fixed_now,
            expected_return_date=fixed_now + timedelta(days=14),
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )


class TestCreateLoan(TestLoanServiceFixtures):
    @pytest.mark.asyncio
    async def test_create_loan_success(
        self, loan_service, sample_book, sample_user, sample_loan_create
    ):
        loan_service.user_repository.find_by_id.return_value = sample_user
        loan_service.loan_repository.count_active_loans_by_user.return_value = 0
        loan_service.loan_repository.find_overdue_loans_by_user.return_value = None
        loan_service.book_repository.find_by_id_with_lock.return_value = sample_book

        created_loan = Loan(
            id=10,
            user_id=sample_loan_create.user_id,
            book_id=sample_loan_create.book_id,
            loan_date=loan_service.get_now(),
            expected_return_date=loan_service.get_now() + timedelta(days=14),
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )
        loan_service.loan_repository.create.return_value = created_loan

        with patch(
            "app.domains.loans.services.AuditLogService.log_event", new=AsyncMock()
        ):
            loan = await loan_service.create_loan(sample_loan_create)

        assert loan.user_id == 1
        assert loan.status == LoanStatus.ACTIVE
        assert sample_book.available_copies == 2
        loan_service.book_repository.update.assert_awaited_once()
        loan_service.loan_repository.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_loan_user_not_found(self, loan_service, sample_loan_create):
        loan_service.user_repository.find_by_id.return_value = None

        with pytest.raises(LookupError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert ErrorMessages.USER_NOT_FOUND in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_loan_book_not_found(
        self, loan_service, sample_user, sample_loan_create
    ):
        loan_service.user_repository.find_by_id.return_value = sample_user
        loan_service.loan_repository.count_active_loans_by_user.return_value = 0
        loan_service.loan_repository.find_overdue_loans_by_user.return_value = None
        loan_service.book_repository.find_by_id_with_lock.return_value = None

        with pytest.raises(LookupError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert ErrorMessages.BOOK_NOT_FOUND in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_loan_book_unavailable(
        self,
        loan_service,
        sample_book_no_copies,
        sample_user,
        sample_loan_create,
    ):
        loan_service.user_repository.find_by_id.return_value = sample_user
        loan_service.loan_repository.count_active_loans_by_user.return_value = 0
        loan_service.loan_repository.find_overdue_loans_by_user.return_value = None
        loan_service.book_repository.find_by_id_with_lock.return_value = (
            sample_book_no_copies
        )

        with pytest.raises(ValueError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert ErrorMessages.BOOK_NOT_AVAILABLE in str(exc.value)

    @pytest.mark.asyncio
    @patch("app.domains.loans.services.settings")
    async def test_create_loan_user_at_limit(
        self,
        mock_settings,
        loan_service,
        sample_book,
        sample_user,
        sample_loan_create,
    ):
        mock_settings.MAX_ACTIVE_LOANS = 3
        loan_service.user_repository.find_by_id.return_value = sample_user
        loan_service.loan_repository.count_active_loans_by_user.return_value = 3

        with pytest.raises(ValueError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert "limite" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_loan_user_has_overdue(
        self,
        loan_service,
        sample_book,
        sample_user,
        sample_loan_create,
        sample_active_loan,
    ):
        loan_service.user_repository.find_by_id.return_value = sample_user
        loan_service.loan_repository.count_active_loans_by_user.return_value = 1
        loan_service.loan_repository.find_overdue_loans_by_user.return_value = (
            sample_active_loan
        )
        loan_service.book_repository.find_by_id_with_lock.return_value = sample_book

        with pytest.raises(ValueError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert ErrorMessages.LOAN_USER_HAS_OVERDUE in str(exc.value)


class TestReturnLoan(TestLoanServiceFixtures):
    @pytest.mark.asyncio
    async def test_return_loan_success_no_fine(
        self, loan_service, sample_active_loan, sample_book, fixed_now
    ):
        sample_active_loan.expected_return_date = fixed_now + timedelta(days=7)
        loan_service.loan_repository.find_by_id_with_lock.return_value = (
            sample_active_loan
        )
        loan_service.book_repository.find_by_id_with_lock.return_value = sample_book

        with patch(
            "app.domains.loans.services.AuditLogService.log_event", new=AsyncMock()
        ):
            result = await loan_service.return_loan(loan_id=1)

        assert result["fine_amount"] == "R$ 0.00"
        assert result["days_overdue"] == 0
        assert sample_active_loan.status == LoanStatus.RETURNED

    @pytest.mark.asyncio
    @patch("app.domains.loans.services.settings")
    async def test_return_loan_with_fine(
        self, mock_settings, loan_service, sample_book, fixed_now
    ):
        mock_settings.DAILY_FINE = Decimal("2.00")

        overdue_loan = Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=fixed_now - timedelta(days=20),
            expected_return_date=fixed_now - timedelta(days=5),
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )

        loan_service.loan_repository.find_by_id_with_lock.return_value = overdue_loan
        loan_service.book_repository.find_by_id_with_lock.return_value = sample_book

        with patch(
            "app.domains.loans.services.AuditLogService.log_event", new=AsyncMock()
        ):
            result = await loan_service.return_loan(loan_id=1)

        assert result["days_overdue"] == 5
        assert result["fine_amount"] == "R$ 10.00"
        assert overdue_loan.fine_amount == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_return_loan_not_found(self, loan_service):
        loan_service.loan_repository.find_by_id_with_lock.return_value = None

        with pytest.raises(LookupError) as exc:
            await loan_service.return_loan(loan_id=999)

        assert ErrorMessages.LOAN_NOT_FOUND in str(exc.value)

    @pytest.mark.asyncio
    async def test_return_loan_already_returned(self, loan_service, fixed_now):
        returned_loan = Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=fixed_now - timedelta(days=10),
            expected_return_date=fixed_now - timedelta(days=3),
            return_date=fixed_now,
            status=LoanStatus.RETURNED,
            fine_amount=Decimal("0.00"),
        )
        loan_service.loan_repository.find_by_id_with_lock.return_value = returned_loan

        with pytest.raises(ValueError) as exc:
            await loan_service.return_loan(loan_id=1)

        assert ErrorMessages.LOAN_ALREADY_RETURNED in str(exc.value)

    @pytest.mark.asyncio
    async def test_return_loan_increments_available_copies(
        self, loan_service, sample_active_loan, sample_book, fixed_now
    ):
        initial_copies = sample_book.available_copies
        sample_active_loan.expected_return_date = fixed_now + timedelta(days=7)
        loan_service.loan_repository.find_by_id_with_lock.return_value = (
            sample_active_loan
        )
        loan_service.book_repository.find_by_id_with_lock.return_value = sample_book

        with patch(
            "app.domains.loans.services.AuditLogService.log_event", new=AsyncMock()
        ):
            await loan_service.return_loan(loan_id=1)

        assert sample_book.available_copies == initial_copies + 1


class TestExtendLoan(TestLoanServiceFixtures):
    @pytest.mark.asyncio
    async def test_extend_loan_success(self, loan_service, sample_active_loan):
        loan_service.loan_repository.find_by_id_with_lock.return_value = (
            sample_active_loan
        )

        with (
            patch("app.domains.loans.services.settings", settings),
            patch(
                "app.domains.loans.services.AuditLogService.log_event", new=AsyncMock()
            ),
        ):
            updated = await loan_service.extend_loan(loan_id=1)

        assert updated.expected_return_date > sample_active_loan.loan_date

    @pytest.mark.asyncio
    async def test_extend_loan_overdue_raises(self, loan_service, fixed_now):
        overdue_loan = Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=fixed_now - timedelta(days=20),
            expected_return_date=fixed_now - timedelta(days=5),
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )
        loan_service.loan_repository.find_by_id_with_lock.return_value = overdue_loan

        with pytest.raises(ValueError) as exc:
            await loan_service.extend_loan(loan_id=1)

        assert ErrorMessages.LOAN_RENEW_OVERDUE in str(exc.value)


class TestListLoans(TestLoanServiceFixtures):
    @pytest.mark.asyncio
    async def test_list_loans_marks_overdue(self, loan_service, fixed_now):
        overdue_loan = Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=fixed_now - timedelta(days=20),
            expected_return_date=fixed_now - timedelta(days=5),
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )
        loan_service.loan_repository.find_all.return_value = [overdue_loan]

        loans = await loan_service.list_loans()

        assert loans[0].status == LoanStatus.OVERDUE


class TestInvalidateBooksCache(TestLoanServiceFixtures):
    @pytest.mark.asyncio
    async def test_invalidate_books_cache_calls_redis(self, loan_service, mock_redis):
        async def scan_iter(match):
            for key in ["books:list:0:10::", "books:list:0:10:title:"]:
                yield key

        mock_redis.scan_iter = scan_iter

        await loan_service._invalidate_books_cache()

        assert mock_redis.delete.await_count == 2


class TestExportLoansCSV(TestLoanServiceFixtures):
    @pytest.fixture
    def sample_book_for_export(self):
        return Book(
            id=1,
            title="Python Programming",
            author="Test Author",
            isbn="ISBN-123456",
            total_copies=5,
            available_copies=3,
        )

    @pytest.fixture
    def sample_user_for_export(self):
        return User(
            id=1, name="John Doe", email="john@test.com", hashed_password="hash"
        )

    @pytest.mark.asyncio
    async def test_export_loans_csv_success(
        self,
        loan_service,
        sample_book_for_export,
        sample_user_for_export,
        fixed_now,
    ):
        loan = Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=fixed_now - timedelta(days=10),
            expected_return_date=fixed_now - timedelta(days=1),
            return_date=fixed_now,
            status=LoanStatus.RETURNED,
            fine_amount=Decimal("4.00"),
        )
        loan.user = sample_user_for_export
        loan.book = sample_book_for_export

        loan_service.loan_repository.find_all_with_relations.side_effect = [
            [loan],
            [],
        ]

        csv_chunks = []
        async for chunk in loan_service.export_loans_csv():
            csv_chunks.append(chunk)

        csv_data = "".join(csv_chunks)

        assert "ID" in csv_data
        assert "John Doe" in csv_data
        assert "Python Programming" in csv_data
        assert "RETURNED" in csv_data

    @pytest.mark.asyncio
    async def test_export_loans_csv_empty(self, loan_service):
        loan_service.loan_repository.find_all_with_relations.return_value = []

        csv_chunks = []
        async for chunk in loan_service.export_loans_csv():
            csv_chunks.append(chunk)

        csv_data = "".join(csv_chunks)
        assert "ID" in csv_data
        assert len(csv_data.strip().split("\n")) == 1
