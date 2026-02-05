import pytest
from pydantic import ValidationError
from app.domains.books.schemas import BookCreate
from app.domains.users.schemas import UserCreate
from app.domains.loans.schemas import LoanCreate


def test_book_create_valid():
    book = BookCreate(title="Test", author="Author", isbn="123", total_copies=5)
    assert book.title == "Test"
    assert book.total_copies == 5


def test_book_create_invalid_copies():

    with pytest.raises(ValidationError) as exc:
        BookCreate(title="T", author="A", isbn="1", total_copies=0)
    assert "Input should be greater than or equal to 1" in str(exc.value)


def test_book_create_negative_copies():
    with pytest.raises(ValidationError) as exc:
        BookCreate(title="T", author="A", isbn="1", total_copies=-5)
    assert "Input should be greater than or equal to 1" in str(exc.value)


def test_book_create_missing_fields():
    with pytest.raises(ValidationError) as exc:
        BookCreate(title="T") # type: ignore
    assert "Field required" in str(exc.value)


def test_book_create_empty_strings():
    with pytest.raises(ValidationError) as exc:
        BookCreate(title="", author="A", isbn="1", total_copies=1)
    assert "String should have at least 1 character" in str(exc.value)


def test_user_create_valid():
    user = UserCreate(name="User", email="user@valid.com", password="secret")
    assert user.email == "user@valid.com"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError) as exc:
        UserCreate(name="User", email="invalid-email", password="secret")
    assert "value is not a valid email address" in str(exc.value)


def test_user_create_empty_name():
    with pytest.raises(ValidationError):
        UserCreate(name="", email="a@b.com", password="secret")


def test_loan_create_valid():
    loan = LoanCreate(user_id=1, book_id=10)
    assert loan.user_id == 1
    assert loan.book_id == 10


def test_loan_create_invalid_types():
    with pytest.raises(ValidationError) as exc:
        LoanCreate(user_id="not-an-int", book_id=10) # type: ignore
    assert "Input should be a valid integer" in str(exc.value)
