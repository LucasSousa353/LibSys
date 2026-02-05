import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.domains.books.schemas import BookCreate, BookResponse
from app.domains.users.schemas import UserCreate, UserResponse
from app.domains.loans.schemas import LoanCreate, LoanResponse


class TestBookCreateSchema:
    def test_valid_book_create(self):
        book = BookCreate(
            title="Clean Code",
            author="Robert Martin",
            isbn="978-0132350884",
            total_copies=5,
        )

        assert book.title == "Clean Code"
        assert book.author == "Robert Martin"
        assert book.isbn == "978-0132350884"
        assert book.total_copies == 5

    def test_book_with_minimum_copies(self):
        book = BookCreate(title="Test", author="Author", isbn="123", total_copies=1)

        assert book.total_copies == 1

    def test_book_with_default_copies(self):
        book = BookCreate(title="Test", author="Author", isbn="123")

        assert book.total_copies == 1

    def test_book_with_large_copies(self):
        book = BookCreate(
            title="Popular Book",
            author="Famous Author",
            isbn="LARGE-001",
            total_copies=1000,
        )

        assert book.total_copies == 1000

    def test_book_zero_copies_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(title="Test", author="Author", isbn="123", total_copies=0)

        assert "greater than or equal to 1" in str(exc.value)

    def test_book_negative_copies_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(title="Test", author="Author", isbn="123", total_copies=-5)

        assert "greater than or equal to 1" in str(exc.value)

    def test_book_missing_title_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(author="Author", isbn="123", total_copies=1)  # type: ignore

        assert "title" in str(exc.value).lower()

    def test_book_missing_author_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(title="Title", isbn="123", total_copies=1)  # type: ignore

        assert "author" in str(exc.value).lower()

    def test_book_missing_isbn_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(title="Title", author="Author", total_copies=1)  # type: ignore

        assert "isbn" in str(exc.value).lower()

    def test_book_empty_title_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(title="", author="Author", isbn="123", total_copies=1)

        assert "não pode ser vazio" in str(exc.value).lower()

    def test_book_empty_author_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(title="Title", author="", isbn="123", total_copies=1)

        assert "não pode ser vazio" in str(exc.value).lower()

    def test_book_whitespace_only_title(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(title="   ", author="Author", isbn="123", total_copies=1)

        assert "campo" in str(exc.value).lower()

    def test_book_whitespace_only_author(self):
        with pytest.raises(ValidationError) as exc:
            BookCreate(title="Title", author="   ", isbn="123", total_copies=1)

        assert "campo" in str(exc.value).lower()

    def test_book_special_characters_in_fields(self):
        book = BookCreate(
            title="Book: A Novel (2nd Ed.)",
            author="O'Brien, John-Paul",
            isbn="978-3-16-148410-0",
            total_copies=3,
        )

        assert "O'Brien" in book.author
        assert ":" in book.title

    def test_book_unicode_characters(self):
        book = BookCreate(
            title="日本語タイトル", author="著者名", isbn="ISBN-日本", total_copies=2
        )

        assert book.title == "日本語タイトル"


class TestUserCreateSchema:
    def test_valid_user_create(self):
        user = UserCreate(
            name="John Doe", email="john@example.com", password="securepassword123"
        )

        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.password == "securepassword123"

    def test_user_valid_email_formats(self):
        valid_emails = [
            "simple@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
            "test@subdomain.domain.com",
        ]

        for email in valid_emails:
            user = UserCreate(name="Test", email=email, password="password123")
            assert user.email == email

    def test_user_invalid_email_raises_validation_error(self):
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(name="Test", email=email, password="password123")

    def test_user_whitespace_only_name_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            UserCreate(name="   ", email="john@example.com", password="password123")

        assert "nome" in str(exc.value).lower()

    def test_user_empty_name_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            UserCreate(name="", email="test@example.com", password="password123")

        assert "não pode ser vazio" in str(exc.value).lower()

    def test_user_missing_name_raises_validation_error(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="password123")  # type: ignore

    def test_user_missing_email_raises_validation_error(self):
        with pytest.raises(ValidationError):
            UserCreate(name="Test", password="password123")  # type: ignore

    def test_user_missing_password_raises_validation_error(self):
        with pytest.raises(ValidationError):
            UserCreate(name="Test", email="test@example.com")  # type: ignore

    def test_user_password_minimum_length(self):
        user = UserCreate(name="Test", email="test@example.com", password="123456")

        assert len(user.password) == 6

    def test_user_password_too_short_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            UserCreate(name="Test", email="test@example.com", password="12345")

        assert "at least 6 character" in str(exc.value)

    def test_user_long_password(self):
        long_password = "a" * 100
        user = UserCreate(name="Test", email="test@example.com", password=long_password)

        assert len(user.password) == 100

    def test_user_unicode_name(self):
        user = UserCreate(
            name="José García", email="jose@example.com", password="password123"
        )

        assert user.name == "José García"


class TestLoanCreateSchema:
    def test_valid_loan_create(self):
        loan = LoanCreate(user_id=1, book_id=10)

        assert loan.user_id == 1
        assert loan.book_id == 10

    def test_loan_with_large_ids(self):
        loan = LoanCreate(user_id=999999, book_id=888888)

        assert loan.user_id == 999999
        assert loan.book_id == 888888

    def test_loan_missing_user_id_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LoanCreate(book_id=10)  # type: ignore

    def test_loan_missing_book_id_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LoanCreate(user_id=1)  # type: ignore

    def test_loan_invalid_user_id_type_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            LoanCreate(user_id="not-an-int", book_id=10)  # type: ignore

        assert "valid integer" in str(exc.value)

    def test_loan_invalid_book_id_type_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            LoanCreate(user_id=1, book_id="abc")  # type: ignore

        assert "valid integer" in str(exc.value)

    def test_loan_float_id_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            LoanCreate(user_id=1.9, book_id=2.1)  # type: ignore

        assert "int_from_float" in str(exc.value)


class TestBookResponseSchema:
    def test_book_response_from_attributes(self):
        class MockBook:
            id = 1
            title = "Test Book"
            author = "Test Author"
            isbn = "TEST-001"
            total_copies = 5
            available_copies = 3

        response = BookResponse.model_validate(MockBook())

        assert response.id == 1
        assert response.title == "Test Book"
        assert response.available_copies == 3


class TestUserResponseSchema:
    def test_user_response_from_attributes(self):
        from datetime import datetime

        class MockUser:
            id = 1
            name = "Test User"
            email = "test@example.com"
            created_at = datetime(2025, 1, 1, 12, 0, 0)

        response = UserResponse.model_validate(MockUser())

        assert response.id == 1
        assert response.name == "Test User"
        assert response.email == "test@example.com"


class TestLoanResponseSchema:
    def test_loan_response_from_attributes(self):
        from datetime import datetime
        from app.domains.loans.models import LoanStatus

        class MockLoan:
            id = 1
            book_id = 10
            user_id = 5
            loan_date = datetime(2025, 1, 1)
            expected_return_date = datetime(2025, 1, 15)
            return_date = None
            status = LoanStatus.ACTIVE
            fine_amount = Decimal("0.00")

        response = LoanResponse.model_validate(MockLoan())

        assert response.id == 1
        assert response.status == LoanStatus.ACTIVE
        assert response.fine_amount == Decimal("0.00")
