import factory
from factory import LazyAttribute, Sequence # type: ignore
from faker import Faker

from app.domains.users.models import User
from app.domains.books.models import Book
from app.domains.loans.models import Loan, LoanStatus
from app.domains.auth.security import get_password_hash
from datetime import datetime, timedelta, timezone

fake = Faker()


class UserFactory(factory.Factory): # type: ignore
    class Meta: # type: ignore
        model = User

    name = LazyAttribute(lambda _: fake.name())
    email = Sequence(lambda n: f"user{n}@example.com")
    hashed_password = LazyAttribute(lambda _: get_password_hash("password123"))


class BookFactory(factory.Factory): # type: ignore
    class Meta: # type: ignore
        model = Book

    title = LazyAttribute(lambda _: fake.sentence(nb_words=3))
    author = LazyAttribute(lambda _: fake.name())
    isbn = Sequence(lambda n: f"ISBN-{n:06d}")
    total_copies = 5
    available_copies = 5


class LoanFactory(factory.Factory): # type: ignore
    class Meta: # type: ignore
        model = Loan

    user_id = None
    book_id = None
    loan_date = LazyAttribute(lambda _: datetime.now(timezone.utc))
    expected_return_date = LazyAttribute(lambda obj: obj.loan_date + timedelta(days=14))
    status = LoanStatus.ACTIVE


class OverdueLoanFactory(LoanFactory):
    loan_date = LazyAttribute(lambda _: datetime.now(timezone.utc) - timedelta(days=30))
    expected_return_date = LazyAttribute(
        lambda _: datetime.now(timezone.utc) - timedelta(days=16)
    )
    status = LoanStatus.ACTIVE


class ReturnedLoanFactory(LoanFactory):
    loan_date = LazyAttribute(lambda _: datetime.now(timezone.utc) - timedelta(days=20))
    expected_return_date = LazyAttribute(
        lambda _: datetime.now(timezone.utc) - timedelta(days=6)
    )
    return_date = LazyAttribute(
        lambda _: datetime.now(timezone.utc) - timedelta(days=5)
    )
    status = LoanStatus.RETURNED
