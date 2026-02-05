import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domains.loans.services import LoanService
from app.domains.loans.schemas import LoanCreate
from app.domains.loans.models import Loan, LoanStatus
from app.domains.books.models import Book
from app.domains.users.models import User
from app.core.config import settings

MAX_ACTIVE_LOANS = settings.MAX_ACTIVE_LOANS
DAILY_FINE = settings.DAILY_FINE


@pytest.fixture
def mock_db_session():
    session = AsyncMock()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.delete = AsyncMock()

    async def _scan_iter(match):

        if False:
            yield None

    redis.scan_iter.side_effect = _scan_iter
    return redis


@pytest.fixture
def loan_service(mock_db_session, mock_redis):
    return LoanService(mock_db_session, mock_redis)


@pytest.mark.asyncio
async def test_create_loan_success(loan_service, mock_db_session):

    loan_in = LoanCreate(user_id=1, book_id=1)

    mock_book = Book(id=1, available_copies=2, title="Test Book")
    mock_user = User(id=1, name="Test User")

    mock_result_book = MagicMock()
    mock_result_book.scalar_one_or_none.return_value = mock_book

    mock_result_user = MagicMock()
    mock_result_user.scalar_one_or_none.return_value = mock_user

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = 0

    mock_result_overdue = MagicMock()
    mock_result_overdue.first.return_value = None

    mock_db_session.execute.side_effect = [
        mock_result_book,
        mock_result_user,
        mock_result_count,
        mock_result_overdue,
    ]

    new_loan = await loan_service.create_loan(loan_in)

    assert new_loan.user_id == 1
    assert new_loan.book_id == 1
    assert new_loan.status == LoanStatus.ACTIVE
    assert mock_book.available_copies == 1

    assert mock_db_session.add.call_count == 2
    assert mock_db_session.commit.called
    assert mock_db_session.refresh.called


@pytest.mark.asyncio
async def test_create_loan_book_not_found(loan_service, mock_db_session):
    loan_in = LoanCreate(user_id=1, book_id=99)

    mock_result_book = MagicMock()
    mock_result_book.scalar_one_or_none.return_value = None

    mock_db_session.execute.side_effect = [mock_result_book]

    with pytest.raises(LookupError, match="Livro não encontrado"):
        await loan_service.create_loan(loan_in)


@pytest.mark.asyncio
async def test_create_loan_no_stock(loan_service, mock_db_session):
    loan_in = LoanCreate(user_id=1, book_id=1)

    mock_book = Book(id=1, available_copies=0)

    mock_result_book = MagicMock()
    mock_result_book.scalar_one_or_none.return_value = mock_book

    mock_db_session.execute.side_effect = [mock_result_book]

    with pytest.raises(ValueError, match="Livro não disponível no estoque"):
        await loan_service.create_loan(loan_in)


@pytest.mark.asyncio
async def test_create_loan_user_limit_reached(loan_service, mock_db_session):
    loan_in = LoanCreate(user_id=1, book_id=1)

    mock_book = Book(id=1, available_copies=5)
    mock_user = User(id=1)

    mock_result_book = MagicMock()
    mock_result_book.scalar_one_or_none.return_value = mock_book

    mock_result_user = MagicMock()
    mock_result_user.scalar_one_or_none.return_value = mock_user

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = MAX_ACTIVE_LOANS

    mock_db_session.execute.side_effect = [
        mock_result_book,
        mock_result_user,
        mock_result_count,
    ]

    with pytest.raises(
        ValueError, match=f"Usuário atingiu o limite de {MAX_ACTIVE_LOANS}"
    ):
        await loan_service.create_loan(loan_in)


@pytest.mark.asyncio
async def test_return_loan_success(loan_service, mock_db_session):
    loan_id = 10

    mock_loan = Loan(
        id=loan_id,
        book_id=5,
        status=LoanStatus.ACTIVE,
        expected_return_date=datetime.now(timezone.utc) + timedelta(days=5),
        fine_amount=Decimal("0.00"),
    )

    mock_book = Book(id=5, available_copies=1)

    mock_result_loan = MagicMock()
    mock_result_loan.scalar_one_or_none.return_value = mock_loan

    mock_result_book = MagicMock()
    mock_result_book.scalar_one_or_none.return_value = mock_book

    mock_db_session.execute.side_effect = [mock_result_loan, mock_result_book]

    result = await loan_service.return_loan(loan_id)

    assert result["message"] == "Livro retornado."
    assert result["fine_amount"] == "R$ 0.00"

    assert mock_loan.status == LoanStatus.RETURNED
    assert mock_loan.return_date is not None
    assert mock_book.available_copies == 2


@pytest.mark.asyncio
async def test_return_loan_with_fine(loan_service, mock_db_session):
    loan_id = 11

    past_date = datetime.now(timezone.utc) - timedelta(days=5)

    mock_loan = Loan(
        id=loan_id,
        book_id=5,
        status=LoanStatus.ACTIVE,
        expected_return_date=past_date,
        fine_amount=Decimal("0.00"),
    )

    mock_book = Book(id=5, available_copies=1)

    mock_db_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_loan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_book)),
    ]

    result = await loan_service.return_loan(loan_id)

    assert mock_loan.fine_amount == Decimal("10.00")
    assert result["days_overdue"] == 5


@pytest.mark.asyncio
async def test_list_loans_updates_overdue(loan_service, mock_db_session):

    past_date = datetime.now(timezone.utc) - timedelta(days=1)

    mock_loan = Loan(id=1, status=LoanStatus.ACTIVE, expected_return_date=past_date)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_loan]

    mock_db_session.execute.return_value = mock_result

    loans = await loan_service.list_loans()

    assert len(loans) == 1
    assert loans[0].status == LoanStatus.OVERDUE
