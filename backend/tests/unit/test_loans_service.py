import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.domains.loans.services import LoanService
from app.domains.loans.schemas import LoanCreate
from app.domains.loans.models import Loan, LoanStatus
from app.domains.books.models import Book
from app.domains.users.models import User


class TestLoanServiceFixtures:
    @pytest.fixture
    def fixed_now(self):
        return datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
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
        return LoanService(mock_db, mock_redis, get_now_fn=lambda: fixed_now)

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
        self, loan_service, mock_db, sample_book, sample_user, sample_loan_create
    ):
        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = sample_user

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        overdue_result = MagicMock()
        overdue_result.first.return_value = None

        async def execute(statement):
            sql = str(statement).lower()
            if "from books" in sql:
                return book_result
            if "from users" in sql:
                return user_result
            if "count" in sql:
                return count_result
            return overdue_result

        mock_db.execute.side_effect = execute

        loan = await loan_service.create_loan(sample_loan_create)

        assert loan.user_id == 1
        assert loan.book_id == 1
        assert loan.status == LoanStatus.ACTIVE
        assert loan.fine_amount == Decimal("0.00")
        assert mock_db.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_create_loan_book_not_found_raises_lookup_error(
        self, loan_service, mock_db, sample_loan_create
    ):
        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = book_result

        with pytest.raises(LookupError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert "Livro não encontrado" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_loan_book_unavailable_raises_value_error(
        self, loan_service, mock_db, sample_book_no_copies, sample_loan_create
    ):
        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book_no_copies
        mock_db.execute.return_value = book_result

        with pytest.raises(ValueError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert "não disponível" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_loan_user_not_found_raises_lookup_error(
        self, loan_service, mock_db, sample_book, sample_loan_create
    ):
        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None

        async def execute(statement):
            sql = str(statement).lower()
            if "from books" in sql:
                return book_result
            return user_result

        mock_db.execute.side_effect = execute

        with pytest.raises(LookupError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert "Usuário não localizado" in str(exc.value)

    @pytest.mark.asyncio
    @patch("app.domains.loans.services.settings")
    async def test_create_loan_user_at_limit_raises_value_error(
        self,
        mock_settings,
        loan_service,
        mock_db,
        sample_book,
        sample_user,
        sample_loan_create,
    ):
        mock_settings.MAX_ACTIVE_LOANS = 3

        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = sample_user

        count_result = MagicMock()
        count_result.scalar.return_value = 3

        async def execute(statement):
            sql = str(statement).lower()
            if "from books" in sql:
                return book_result
            if "from users" in sql:
                return user_result
            return count_result

        mock_db.execute.side_effect = execute

        with pytest.raises(ValueError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert "limite" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_loan_user_has_overdue_raises_value_error(
        self,
        loan_service,
        mock_db,
        sample_book,
        sample_user,
        sample_loan_create,
        sample_active_loan,
    ):
        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = sample_user

        count_result = MagicMock()
        count_result.scalar.return_value = 1

        overdue_result = MagicMock()
        overdue_result.first.return_value = sample_active_loan

        async def execute(statement):
            sql = str(statement).lower()
            if "from books" in sql:
                return book_result
            if "from users" in sql:
                return user_result
            if "count" in sql:
                return count_result
            return overdue_result

        mock_db.execute.side_effect = execute

        with pytest.raises(ValueError) as exc:
            await loan_service.create_loan(sample_loan_create)

        assert "atrasados" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_loan_decrements_available_copies(
        self, loan_service, mock_db, sample_book, sample_user, sample_loan_create
    ):
        initial_copies = sample_book.available_copies

        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = sample_user

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        overdue_result = MagicMock()
        overdue_result.first.return_value = None

        async def execute(statement):
            sql = str(statement).lower()
            if "from books" in sql:
                return book_result
            if "from users" in sql:
                return user_result
            if "count" in sql:
                return count_result
            return overdue_result

        mock_db.execute.side_effect = execute

        await loan_service.create_loan(sample_loan_create)

        assert sample_book.available_copies == initial_copies - 1


class TestReturnLoan(TestLoanServiceFixtures):
    @pytest.mark.asyncio
    async def test_return_loan_success_no_fine(
        self, loan_service, mock_db, sample_active_loan, sample_book, fixed_now
    ):
        sample_active_loan.expected_return_date = fixed_now + timedelta(days=7)

        loan_result = MagicMock()
        loan_result.scalar_one_or_none.return_value = sample_active_loan

        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book

        async def execute(statement):
            sql = str(statement).lower()
            if "from loans" in sql:
                return loan_result
            return book_result

        mock_db.execute.side_effect = execute

        result = await loan_service.return_loan(loan_id=1, current_user_id=1)

        assert result["fine_amount"] == "R$ 0.00"
        assert result["days_overdue"] == 0
        assert sample_active_loan.status == LoanStatus.RETURNED

    @pytest.mark.asyncio
    @patch("app.domains.loans.services.settings")
    async def test_return_loan_with_fine(
        self, mock_settings, loan_service, mock_db, sample_book, fixed_now
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

        loan_result = MagicMock()
        loan_result.scalar_one_or_none.return_value = overdue_loan

        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book

        async def execute(statement):
            sql = str(statement).lower()
            if "from loans" in sql:
                return loan_result
            return book_result

        mock_db.execute.side_effect = execute

        result = await loan_service.return_loan(loan_id=1, current_user_id=1)

        assert result["days_overdue"] == 5
        assert result["fine_amount"] == "R$ 10.00"
        assert overdue_loan.fine_amount == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_return_loan_not_found_raises_lookup_error(
        self, loan_service, mock_db
    ):
        loan_result = MagicMock()
        loan_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = loan_result

        with pytest.raises(LookupError) as exc:
            await loan_service.return_loan(loan_id=999, current_user_id=1)

        assert "não encontrado" in str(exc.value)

    @pytest.mark.asyncio
    async def test_return_loan_wrong_user_raises_permission_error(
        self, loan_service, mock_db, sample_active_loan
    ):
        sample_active_loan.user_id = 2

        loan_result = MagicMock()
        loan_result.scalar_one_or_none.return_value = sample_active_loan
        mock_db.execute.return_value = loan_result

        with pytest.raises(PermissionError) as exc:
            await loan_service.return_loan(loan_id=1, current_user_id=1)

        assert "só pode devolver" in str(exc.value)

    @pytest.mark.asyncio
    async def test_return_loan_already_returned_raises_value_error(
        self, loan_service, mock_db, fixed_now
    ):
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

        loan_result = MagicMock()
        loan_result.scalar_one_or_none.return_value = returned_loan
        mock_db.execute.return_value = loan_result

        with pytest.raises(ValueError) as exc:
            await loan_service.return_loan(loan_id=1, current_user_id=1)

        assert "já devolvido" in str(exc.value)

    @pytest.mark.asyncio
    async def test_return_loan_increments_available_copies(
        self, loan_service, mock_db, sample_active_loan, sample_book, fixed_now
    ):
        initial_copies = sample_book.available_copies
        sample_active_loan.expected_return_date = fixed_now + timedelta(days=7)

        loan_result = MagicMock()
        loan_result.scalar_one_or_none.return_value = sample_active_loan

        book_result = MagicMock()
        book_result.scalar_one_or_none.return_value = sample_book

        async def execute(statement):
            sql = str(statement).lower()
            if "from loans" in sql:
                return loan_result
            return book_result

        mock_db.execute.side_effect = execute

        await loan_service.return_loan(loan_id=1, current_user_id=1)

        assert sample_book.available_copies == initial_copies + 1


class TestListLoans(TestLoanServiceFixtures):
    @pytest.mark.asyncio
    async def test_list_loans_no_filters(
        self, loan_service, mock_db, sample_active_loan, fixed_now
    ):
        sample_active_loan.expected_return_date = fixed_now + timedelta(days=7)

        result = MagicMock()
        result.scalars.return_value.all.return_value = [sample_active_loan]
        mock_db.execute.return_value = result

        loans = await loan_service.list_loans()

        assert len(loans) == 1

    @pytest.mark.asyncio
    async def test_list_loans_filter_by_user_id(
        self, loan_service, mock_db, sample_active_loan, fixed_now
    ):
        sample_active_loan.expected_return_date = fixed_now + timedelta(days=7)

        result = MagicMock()
        result.scalars.return_value.all.return_value = [sample_active_loan]
        mock_db.execute.return_value = result

        loans = await loan_service.list_loans(user_id=1)

        assert len(loans) == 1
        assert loans[0].user_id == 1

    @pytest.mark.asyncio
    async def test_list_loans_filter_by_active_status(
        self, loan_service, mock_db, sample_active_loan, fixed_now
    ):
        sample_active_loan.expected_return_date = fixed_now + timedelta(days=7)

        result = MagicMock()
        result.scalars.return_value.all.return_value = [sample_active_loan]
        mock_db.execute.return_value = result

        loans = await loan_service.list_loans(status=LoanStatus.ACTIVE)

        assert len(loans) == 1

    @pytest.mark.asyncio
    async def test_list_loans_empty_result(self, loan_service, mock_db):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result

        loans = await loan_service.list_loans()

        assert loans == []

    @pytest.mark.asyncio
    async def test_list_loans_pagination(self, loan_service, mock_db):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result

        await loan_service.list_loans(skip=10, limit=5)

        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_loans_marks_overdue_status(
        self, loan_service, mock_db, fixed_now
    ):
        overdue_loan = Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=fixed_now - timedelta(days=20),
            expected_return_date=fixed_now - timedelta(days=5),
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )

        result = MagicMock()
        result.scalars.return_value.all.return_value = [overdue_loan]
        mock_db.execute.return_value = result

        loans = await loan_service.list_loans()

        assert loans[0].status == LoanStatus.OVERDUE


class TestInvalidateBooksCache(TestLoanServiceFixtures):
    @pytest.mark.asyncio
    async def test_invalidate_books_cache_calls_redis(self, loan_service, mock_redis):
        keys_to_delete = ["books:list:0:10::", "books:list:0:10:title:"]

        async def mock_scan_iter(match):
            for key in keys_to_delete:
                yield key

        mock_redis.scan_iter = mock_scan_iter

        await loan_service._invalidate_books_cache()

        assert mock_redis.delete.await_count == len(keys_to_delete)


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

    @pytest.fixture
    def sample_returned_loan(self, fixed_now):
        return Loan(
            id=1,
            user_id=1,
            book_id=1,
            loan_date=fixed_now - timedelta(days=20),
            expected_return_date=fixed_now - timedelta(days=6),
            return_date=fixed_now - timedelta(days=5),
            status=LoanStatus.RETURNED,
            fine_amount=Decimal("4.00"),
        )

    @pytest.mark.asyncio
    async def test_export_loans_csv_success(
        self,
        loan_service,
        mock_db,
        sample_book_for_export,
        sample_user_for_export,
        sample_returned_loan,
        fixed_now,
    ):
        result_find_all_first = MagicMock()
        result_find_all_first.scalars.return_value.all.return_value = [
            sample_returned_loan
        ]

        result_find_all_empty = MagicMock()
        result_find_all_empty.scalars.return_value.all.return_value = []

        result_user = MagicMock()
        result_user.scalar_one_or_none.return_value = sample_user_for_export

        result_book = MagicMock()
        result_book.scalar_one_or_none.return_value = sample_book_for_export

        call_count = 0

        async def execute(statement):
            nonlocal call_count
            sql = str(statement).lower()
            if "from loans" in sql:
                call_count += 1
                # Primeira chamada retorna dados, segunda retorna vazio
                return (
                    result_find_all_first if call_count == 1 else result_find_all_empty
                )
            if "from users" in sql:
                return result_user
            if "from books" in sql:
                return result_book
            return result_find_all_first

        mock_db.execute.side_effect = execute

        # Consumir async generator
        csv_chunks = []
        async for chunk in loan_service.export_loans_csv():
            csv_chunks.append(chunk)

        csv_data = "".join(csv_chunks)

        assert csv_data is not None
        assert isinstance(csv_data, str)
        assert "ID" in csv_data
        assert "Usuário (ID)" in csv_data
        assert "Livro (ID)" in csv_data
        assert "Título do Livro" in csv_data
        assert "Nome do Usuário" in csv_data
        assert "Data do Empréstimo" in csv_data
        assert "Status" in csv_data
        assert "Multa (R$)" in csv_data
        assert "John Doe" in csv_data
        assert "Python Programming" in csv_data
        assert "RETURNED" in csv_data

    @pytest.mark.asyncio
    async def test_export_loans_csv_empty_list(self, loan_service, mock_db):
        result_find_all = MagicMock()
        result_find_all.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_find_all

        csv_chunks = []
        async for chunk in loan_service.export_loans_csv():
            csv_chunks.append(chunk)

        csv_data = "".join(csv_chunks)

        assert csv_data is not None
        assert "ID" in csv_data
        assert "Usuário (ID)" in csv_data
        lines = csv_data.strip().split("\n")
        assert len(lines) == 1

    @pytest.mark.asyncio
    async def test_export_loans_csv_with_user_id_filter(
        self,
        loan_service,
        mock_db,
        sample_book_for_export,
        sample_user_for_export,
        sample_active_loan,
    ):
        result_find_all_first = MagicMock()
        result_find_all_first.scalars.return_value.all.return_value = [
            sample_active_loan
        ]

        result_find_all_empty = MagicMock()
        result_find_all_empty.scalars.return_value.all.return_value = []

        result_user = MagicMock()
        result_user.scalar_one_or_none.return_value = sample_user_for_export

        result_book = MagicMock()
        result_book.scalar_one_or_none.return_value = sample_book_for_export

        call_count = 0

        async def execute(statement):
            nonlocal call_count
            sql = str(statement).lower()
            if "from loans" in sql:
                call_count += 1
                return (
                    result_find_all_first if call_count == 1 else result_find_all_empty
                )
            if "from users" in sql:
                return result_user
            if "from books" in sql:
                return result_book
            return result_find_all_first

        mock_db.execute.side_effect = execute

        csv_chunks = []
        async for chunk in loan_service.export_loans_csv(user_id=1):
            csv_chunks.append(chunk)

        csv_data = "".join(csv_chunks)

        assert csv_data is not None
        assert "John Doe" in csv_data

    @pytest.mark.asyncio
    async def test_export_loans_csv_with_status_filter(
        self,
        loan_service,
        mock_db,
        sample_book_for_export,
        sample_user_for_export,
        sample_active_loan,
    ):
        result_find_all_first = MagicMock()
        result_find_all_first.scalars.return_value.all.return_value = [
            sample_active_loan
        ]

        result_find_all_empty = MagicMock()
        result_find_all_empty.scalars.return_value.all.return_value = []

        result_user = MagicMock()
        result_user.scalar_one_or_none.return_value = sample_user_for_export

        result_book = MagicMock()
        result_book.scalar_one_or_none.return_value = sample_book_for_export

        call_count = 0

        async def execute(statement):
            nonlocal call_count
            sql = str(statement).lower()
            if "from loans" in sql:
                call_count += 1
                return (
                    result_find_all_first if call_count == 1 else result_find_all_empty
                )
            if "from users" in sql:
                return result_user
            if "from books" in sql:
                return result_book
            return result_find_all_first

        mock_db.execute.side_effect = execute

        csv_chunks = []
        async for chunk in loan_service.export_loans_csv(status=LoanStatus.ACTIVE):
            csv_chunks.append(chunk)

        csv_data = "".join(csv_chunks)

        assert csv_data is not None
        assert "ACTIVE" in csv_data

    @pytest.mark.asyncio
    async def test_export_loans_csv_marks_overdue_status(
        self,
        loan_service,
        mock_db,
        sample_book_for_export,
        sample_user_for_export,
        fixed_now,
    ):
        overdue_loan = Loan(
            id=2,
            user_id=1,
            book_id=1,
            loan_date=fixed_now - timedelta(days=20),
            expected_return_date=fixed_now - timedelta(days=5),
            return_date=None,
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )

        result_find_all_first = MagicMock()
        result_find_all_first.scalars.return_value.all.return_value = [overdue_loan]

        result_find_all_empty = MagicMock()
        result_find_all_empty.scalars.return_value.all.return_value = []

        result_user = MagicMock()
        result_user.scalar_one_or_none.return_value = sample_user_for_export

        result_book = MagicMock()
        result_book.scalar_one_or_none.return_value = sample_book_for_export

        call_count = 0

        async def execute(statement):
            nonlocal call_count
            if "from loans" in str(statement).lower():
                call_count += 1
                return (
                    result_find_all_first if call_count == 1 else result_find_all_empty
                )
            if "from users" in str(statement).lower():
                return result_user
            if "from books" in str(statement).lower():
                return result_book
            return result_find_all_first

        mock_db.execute.side_effect = execute

        csv_chunks = []
        async for chunk in loan_service.export_loans_csv():
            csv_chunks.append(chunk)

        csv_data = "".join(csv_chunks)

        assert csv_data is not None
        assert "OVERDUE" in csv_data
