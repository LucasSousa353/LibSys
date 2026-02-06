import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import structlog
from sqlalchemy import select, delete, text

from app.core.base import SessionLocal
from app.core.logging.config import configure_logging
from app.domains.users.models import User
from app.domains.books.models import Book
from app.domains.loans.models import Loan, LoanStatus
from app.domains.auth.security import get_password_hash

configure_logging()
logger = structlog.get_logger()

DEFAULT_USERS = [
    {
        "name": "Admin",
        "email": "admin@libsys.com",
        "password": "admin123",
    },
    {
        "name": "Ana Silva",
        "email": "ana.silva@libsys.com",
        "password": "password123",
    },
    {
        "name": "Joao Souza",
        "email": "joao.souza@libsys.com",
        "password": "password123",
    },
    {
        "name": "Beatriz Lima",
        "email": "beatriz.lima@libsys.com",
        "password": "password123",
    },
    {
        "name": "Carlos Mendes",
        "email": "carlos.mendes@libsys.com",
        "password": "password123",
    },
]

DEFAULT_BOOKS = [
    {
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "isbn": "9780134494166",
        "total_copies": 3,
    },
    {
        "title": "Designing Data-Intensive Applications",
        "author": "Martin Kleppmann",
        "isbn": "9781449373320",
        "total_copies": 4,
    },
    {
        "title": "Refactoring",
        "author": "Martin Fowler",
        "isbn": "9780134757599",
        "total_copies": 2,
    },
    {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "isbn": "9780201616224",
        "total_copies": 5,
    },
    {
        "title": "Patterns of Enterprise Application Architecture",
        "author": "Martin Fowler",
        "isbn": "9780321127426",
        "total_copies": 3,
    },
    {
        "title": "Domain-Driven Design",
        "author": "Eric Evans",
        "isbn": "9780321125217",
        "total_copies": 2,
    },
]

DEFAULT_LOANS = [
    {
        "user_email": "ana.silva@libsys.com",
        "book_isbn": "9780134494166",
        "status": LoanStatus.ACTIVE,
        "loan_days_ago": 3,
        "return_days_ago": None,
    },
    {
        "user_email": "joao.souza@libsys.com",
        "book_isbn": "9781449373320",
        "status": LoanStatus.RETURNED,
        "loan_days_ago": 20,
        "return_days_ago": 5,
    },
    {
        "user_email": "beatriz.lima@libsys.com",
        "book_isbn": "9780134757599",
        "status": LoanStatus.OVERDUE,
        "loan_days_ago": 18,
        "return_days_ago": None,
    },
    {
        "user_email": "carlos.mendes@libsys.com",
        "book_isbn": "9780201616224",
        "status": LoanStatus.OVERDUE,
        "loan_days_ago": 25,
        "return_days_ago": None,
    },
    {
        "user_email": "ana.silva@libsys.com",
        "book_isbn": "9780321127426",
        "status": LoanStatus.ACTIVE,
        "loan_days_ago": 13,
        "return_days_ago": None,
    },
    {
        "user_email": "joao.souza@libsys.com",
        "book_isbn": "9780321125217",
        "status": LoanStatus.ACTIVE,
        "loan_days_ago": 7,
        "return_days_ago": None,
    },
]


def get_now() -> datetime:
    return datetime.now(timezone.utc)


async def reset_database():
    async with SessionLocal() as db:
        await db.execute(text("TRUNCATE TABLE loans, books, users RESTART IDENTITY CASCADE"))
        await db.commit()


async def seed_users():
    created = 0
    async with SessionLocal() as db:
        for user_data in DEFAULT_USERS:
            result = await db.execute(
                select(User).where(User.email == user_data["email"])
            )
            if result.scalar_one_or_none():
                continue

            user = User(
                name=user_data["name"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
            )
            db.add(user)
            created += 1

        if created:
            await db.commit()

    return created


async def seed_books():
    created = 0
    async with SessionLocal() as db:
        for book_data in DEFAULT_BOOKS:
            result = await db.execute(
                select(Book).where(Book.isbn == book_data["isbn"])
            )
            if result.scalar_one_or_none():
                continue

            book = Book(
                title=book_data["title"],
                author=book_data["author"],
                isbn=book_data["isbn"],
                total_copies=book_data["total_copies"],
                available_copies=book_data["total_copies"],
            )
            db.add(book)
            created += 1

        if created:
            await db.commit()

    return created


async def seed_loans():
    created = 0
    async with SessionLocal() as db:
        for loan_data in DEFAULT_LOANS:
            user_result = await db.execute(
                select(User).where(User.email == loan_data["user_email"])
            )
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            book_result = await db.execute(
                select(Book).where(Book.isbn == loan_data["book_isbn"])
            )
            book = book_result.scalar_one_or_none()
            if not book or book.available_copies < 1:
                continue

            existing = await db.execute(
                select(Loan).where(
                    Loan.user_id == user.id,
                    Loan.book_id == book.id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            now = get_now()
            loan_date = now - timedelta(days=loan_data["loan_days_ago"])
            expected_return_date = loan_date + timedelta(days=14)
            return_date = None
            if loan_data["return_days_ago"] is not None:
                return_date = now - timedelta(days=loan_data["return_days_ago"])

            loan = Loan(
                user_id=user.id,
                book_id=book.id,
                loan_date=loan_date,
                expected_return_date=expected_return_date,
                return_date=return_date,
                status=loan_data["status"],
                fine_amount=Decimal("0.00"),
            )

            book.available_copies -= 1
            db.add(book)
            db.add(loan)
            created += 1

        if created:
            await db.commit()

    return created


async def run_seed(reset: bool, with_loans: bool):
    if reset:
        await reset_database()

    users_created = await seed_users()
    books_created = await seed_books()
    loans_created = 0
    if with_loans:
        loans_created = await seed_loans()

    logger.info(
        "seed_completed",
        users_created=users_created,
        books_created=books_created,
        loans_created=loans_created,
    )


def main():
    parser = argparse.ArgumentParser(description="Seed LibSys database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing users, books, and loans before seeding",
    )
    parser.add_argument(
        "--with-loans",
        action="store_true",
        help="Also seed some example loans",
    )
    args = parser.parse_args()

    asyncio.run(run_seed(reset=args.reset, with_loans=args.with_loans))


if __name__ == "__main__":
    main()
