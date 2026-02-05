import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.base import Base
from app.core.config import settings
from app.domains.books.models import Book
from app.domains.loans.models import Loan, LoanStatus
from app.domains.loans.schemas import LoanCreate
from app.domains.loans.services import LoanService
from app.domains.users.models import User


@pytest.fixture
def fixed_now():
    return datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
async def db_session() -> AsyncSession: # type: ignore
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session # type: ignore

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def redis_stub():
    redis = MagicMock()
    redis.delete = AsyncMock()

    async def empty_scan_iter(match):
        return
        yield

    redis.scan_iter = empty_scan_iter
    return redis


class TestLoanServiceWithDb:
    @pytest.mark.asyncio
    async def test_create_loan_with_real_db(self, db_session, redis_stub, fixed_now):
        user = User(name="User", email="user@test.com", hashed_password="hash")
        book = Book(
            title="Book",
            author="Author",
            isbn="ISBN-DB-001",
            total_copies=2,
            available_copies=2,
        )
        db_session.add_all([user, book])
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(book)

        service = LoanService(db_session, redis_stub, get_now_fn=lambda: fixed_now)
        loan = await service.create_loan(LoanCreate(user_id=user.id, book_id=book.id))

        await db_session.refresh(book)
        assert loan.user_id == user.id
        assert loan.book_id == book.id
        assert book.available_copies == 1

    @pytest.mark.asyncio
    async def test_return_loan_with_fine_real_db(
        self, db_session, redis_stub, fixed_now
    ):
        user = User(name="User", email="user2@test.com", hashed_password="hash")
        book = Book(
            title="Book",
            author="Author",
            isbn="ISBN-DB-002",
            total_copies=1,
            available_copies=0,
        )
        db_session.add_all([user, book])
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(book)

        loan = Loan(
            user_id=user.id,
            book_id=book.id,
            loan_date=fixed_now - timedelta(days=20),
            expected_return_date=fixed_now - timedelta(days=5),
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )
        db_session.add(loan)
        await db_session.commit()
        await db_session.refresh(loan)

        service = LoanService(db_session, redis_stub, get_now_fn=lambda: fixed_now)
        result = await service.return_loan(loan_id=loan.id, current_user_id=user.id)

        await db_session.refresh(loan)
        await db_session.refresh(book)
        assert result["days_overdue"] == 5
        assert result["fine_amount"] == f"R$ {(settings.DAILY_FINE * 5):.2f}"
        assert loan.fine_amount == settings.DAILY_FINE * 5
        assert loan.status == LoanStatus.RETURNED
        assert book.available_copies == 1
