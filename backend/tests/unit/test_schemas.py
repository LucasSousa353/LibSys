import pytest
from pydantic import ValidationError
from app.books.schemas import BookCreate
from app.users.schemas import UserCreate


def test_book_create_valid():
    book = BookCreate(title="T", author="A", isbn="1", total_copies=5)
    assert book.title == "T"
    assert book.total_copies == 5


def test_book_create_invalid_copies():
    with pytest.raises(ValidationError):
        BookCreate(title="T", author="A", isbn="1", total_copies=0)


def test_book_create_missing_fields():
    with pytest.raises(ValidationError):
        BookCreate(title="T")  # type: ignore # Missing author, isbn


def test_user_create_valid():
    user = UserCreate(name="U", email="u@u.com")
    assert user.email == "u@u.com"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(name="U", email="invalid-email")
