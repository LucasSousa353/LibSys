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
        "role": "admin",
        "is_active": True,
    },
    {
        "name": "Ana Silva",
        "email": "ana.silva@libsys.com",
        "password": "password123",
        "role": "librarian",
        "is_active": True,
    },
    {
        "name": "Joao Souza",
        "email": "joao.souza@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": True,
    },
    {
        "name": "Beatriz Lima",
        "email": "beatriz.lima@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": True,
    },
    {
        "name": "Carlos Mendes",
        "email": "carlos.mendes@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": True,
    },
    {
        "name": "Maria Santos",
        "email": "maria.santos@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": False,
    },
    {
        "name": "Paulo Oliveira",
        "email": "paulo.oliveira@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": False,
    },
    {
        "name": "Fernanda Costa",
        "email": "fernanda.costa@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": True,
    },
    {
        "name": "Lucas Pereira",
        "email": "lucas.pereira@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": True,
    },
    {
        "name": "Sofia Almeida",
        "email": "sofia.almeida@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": False,
    },
    {
        "name": "Ricardo Nunes",
        "email": "ricardo.nunes@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": True,
    },
    {
        "name": "Juliana Ribeiro",
        "email": "juliana.ribeiro@libsys.com",
        "password": "password123",
        "role": "user",
        "is_active": True,
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
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "9780132350884",
        "total_copies": 4,
    },
    {
        "title": "The Clean Coder",
        "author": "Robert C. Martin",
        "isbn": "9780137081073",
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
        "title": "Working Effectively with Legacy Code",
        "author": "Michael Feathers",
        "isbn": "9780131177055",
        "total_copies": 3,
    },
    {
        "title": "Test Driven Development",
        "author": "Kent Beck",
        "isbn": "9780321146533",
        "total_copies": 3,
    },
    {
        "title": "Release It!",
        "author": "Michael T. Nygard",
        "isbn": "9781680502398",
        "total_copies": 2,
    },
    {
        "title": "Accelerate",
        "author": "Nicole Forsgren",
        "isbn": "9781942788331",
        "total_copies": 4,
    },
    {
        "title": "The Phoenix Project",
        "author": "Gene Kim",
        "isbn": "9780988262591",
        "total_copies": 4,
    },
    {
        "title": "Site Reliability Engineering",
        "author": "Betsy Beyer",
        "isbn": "9781491929124",
        "total_copies": 3,
    },
    {
        "title": "Building Microservices",
        "author": "Sam Newman",
        "isbn": "9781492034025",
        "total_copies": 3,
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
    {
        "user_email": "fernanda.costa@libsys.com",
        "book_isbn": "9780132350884",
        "status": LoanStatus.RETURNED,
        "loan_days_ago": 30,
        "return_days_ago": 10,
    },
    {
        "user_email": "lucas.pereira@libsys.com",
        "book_isbn": "9780137081073",
        "status": LoanStatus.ACTIVE,
        "loan_days_ago": 2,
        "return_days_ago": None,
    },
    {
        "user_email": "ricardo.nunes@libsys.com",
        "book_isbn": "9780131177055",
        "status": LoanStatus.RETURNED,
        "loan_days_ago": 40,
        "return_days_ago": 20,
    },
    {
        "user_email": "juliana.ribeiro@libsys.com",
        "book_isbn": "9780321146533",
        "status": LoanStatus.OVERDUE,
        "loan_days_ago": 22,
        "return_days_ago": None,
    },
    {
        "user_email": "joao.souza@libsys.com",
        "book_isbn": "9781680502398",
        "status": LoanStatus.ACTIVE,
        "loan_days_ago": 4,
        "return_days_ago": None,
    },
    {
        "user_email": "ana.silva@libsys.com",
        "book_isbn": "9781942788331",
        "status": LoanStatus.RETURNED,
        "loan_days_ago": 16,
        "return_days_ago": 3,
    },
    {
        "user_email": "carlos.mendes@libsys.com",
        "book_isbn": "9780988262591",
        "status": LoanStatus.ACTIVE,
        "loan_days_ago": 6,
        "return_days_ago": None,
    },
    {
        "user_email": "beatriz.lima@libsys.com",
        "book_isbn": "9781491929124",
        "status": LoanStatus.OVERDUE,
        "loan_days_ago": 19,
        "return_days_ago": None,
    },
    {
        "user_email": "fernanda.costa@libsys.com",
        "book_isbn": "9781492034025",
        "status": LoanStatus.ACTIVE,
        "loan_days_ago": 5,
        "return_days_ago": None,
    },
]


def get_now() -> datetime:
    return datetime.now(timezone.utc)


async def reset_database():
    async with SessionLocal() as db:
        await db.execute(
            text("TRUNCATE TABLE loans, books, users RESTART IDENTITY CASCADE")
        )
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
                role=user_data.get("role", "user"),
                is_active=user_data.get("is_active", True),
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
