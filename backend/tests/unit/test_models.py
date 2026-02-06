from datetime import datetime, timezone
from decimal import Decimal

from app.domains.books.models import Book
from app.domains.users.models import User
from app.domains.loans.models import Loan, LoanStatus


class TestBookModel:
    def test_book_creation_with_all_fields(self):
        book = Book(
            id=1,
            title="Clean Code",
            author="Robert Martin",
            isbn="978-0132350884",
            total_copies=5,
            available_copies=3,
        )

        assert book.id == 1
        assert book.title == "Clean Code"
        assert book.author == "Robert Martin"
        assert book.isbn == "978-0132350884"
        assert book.total_copies == 5
        assert book.available_copies == 3

    def test_book_tablename(self):
        assert Book.__tablename__ == "books"

    def test_book_default_copies(self):
        book = Book(
            title="Test",
            author="Author",
            isbn="TEST-001",
        )

        assert book.total_copies is None or book.total_copies == 1
        assert book.available_copies is None or book.available_copies == 1

    def test_book_has_loans_relationship(self):
        assert hasattr(Book, "loans")


class TestUserModel:
    def test_user_creation_with_all_fields(self):
        user = User(
            id=1,
            name="John Doe",
            email="john@example.com",
            hashed_password="hashed_value",
            role="user",
            must_reset_password=False,
            is_active=True,
        )

        assert user.id == 1
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.hashed_password == "hashed_value"
        assert user.role == "user"
        assert user.must_reset_password is False
        assert user.is_active is True

    def test_user_tablename(self):
        assert User.__tablename__ == "users"

    def test_user_has_loans_relationship(self):
        assert hasattr(User, "loans")


class TestLoanModel:
    def test_loan_creation_with_all_fields(self):
        now = datetime.now(timezone.utc)
        expected_return = datetime(2025, 2, 18, tzinfo=timezone.utc)

        loan = Loan(
            id=1,
            user_id=10,
            book_id=20,
            loan_date=now,
            expected_return_date=expected_return,
            return_date=None,
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )

        assert loan.id == 1
        assert loan.user_id == 10
        assert loan.book_id == 20
        assert loan.status == LoanStatus.ACTIVE
        assert loan.fine_amount == Decimal("0.00")
        assert loan.return_date is None

    def test_loan_tablename(self):
        assert Loan.__tablename__ == "loans"

    def test_loan_status_active(self):
        loan = Loan(
            user_id=1,
            book_id=1,
            expected_return_date=datetime.now(timezone.utc),
            status=LoanStatus.ACTIVE,
            fine_amount=Decimal("0.00"),
        )

        assert loan.status == LoanStatus.ACTIVE
        assert loan.status.value == "active"

    def test_loan_status_returned(self):
        loan = Loan(
            user_id=1,
            book_id=1,
            expected_return_date=datetime.now(timezone.utc),
            return_date=datetime.now(timezone.utc),
            status=LoanStatus.RETURNED,
            fine_amount=Decimal("0.00"),
        )

        assert loan.status == LoanStatus.RETURNED
        assert loan.status.value == "returned"

    def test_loan_status_overdue(self):
        loan = Loan(
            user_id=1,
            book_id=1,
            expected_return_date=datetime.now(timezone.utc),
            status=LoanStatus.OVERDUE,
            fine_amount=Decimal("10.00"),
        )

        assert loan.status == LoanStatus.OVERDUE
        assert loan.status.value == "overdue"

    def test_loan_with_fine(self):
        loan = Loan(
            user_id=1,
            book_id=1,
            expected_return_date=datetime.now(timezone.utc),
            status=LoanStatus.RETURNED,
            fine_amount=Decimal("15.50"),
        )

        assert loan.fine_amount == Decimal("15.50")

    def test_loan_has_user_relationship(self):
        assert hasattr(Loan, "user")

    def test_loan_has_book_relationship(self):
        assert hasattr(Loan, "book")


class TestLoanStatusEnum:
    def test_loan_status_values(self):
        assert LoanStatus.ACTIVE.value == "active"
        assert LoanStatus.RETURNED.value == "returned"
        assert LoanStatus.OVERDUE.value == "overdue"

    def test_loan_status_is_string_enum(self):
        assert isinstance(LoanStatus.ACTIVE, str)
        assert LoanStatus.ACTIVE == "active"

    def test_loan_status_members(self):
        members = list(LoanStatus)

        assert len(members) == 3
        assert LoanStatus.ACTIVE in members
        assert LoanStatus.RETURNED in members
        assert LoanStatus.OVERDUE in members
