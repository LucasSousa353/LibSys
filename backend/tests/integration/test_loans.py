import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, func

from app.domains.loans.models import Loan, LoanStatus
from app.main import app
from app.core.base import get_db
from app.core.cache.redis import get_redis
from app.domains.auth.dependencies import get_current_user
from tests.factories import BookFactory, UserFactory, LoanFactory, OverdueLoanFactory


class TestCreateLoan:
    @pytest.mark.asyncio
    async def test_create_loan_success(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        book = await create_book()
        response = await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": book.id}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == authenticated_user.id
        assert data["book_id"] == book.id
        assert data["status"] == LoanStatus.ACTIVE.value
        assert "id" in data
        assert "loan_date" in data
        assert "expected_return_date" in data

    @pytest.mark.asyncio
    async def test_create_loan_decrements_available_copies(
        self,
        client: AsyncClient,
        authenticated_user,
        create_book,
        db_session: AsyncSession,
    ):
        book = await create_book(available_copies=5)
        await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": book.id}
        )
        await db_session.refresh(book)
        assert book.available_copies == 4

    @pytest.mark.asyncio
    async def test_create_loan_book_out_of_stock(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        book = await create_book(available_copies=0)
        response = await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": book.id}
        )
        assert response.status_code == 400
        assert "Livro não disponível no estoque" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_loan_book_not_found(
        self, client: AsyncClient, authenticated_user
    ):
        response = await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": 99999}
        )
        assert response.status_code == 404
        assert "Livro não encontrado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_loan_user_not_found(self, client: AsyncClient, create_book):
        book = await create_book()
        response = await client.post(
            "/loans/", json={"user_id": 99999, "book_id": book.id}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_loan_for_other_user_forbidden(
        self, client: AsyncClient, create_book, create_user
    ):
        book = await create_book()
        other_user = await create_user(email="other@user.com")
        response = await client.post(
            "/loans/", json={"user_id": other_user.id, "book_id": book.id}
        )
        assert response.status_code == 403
        assert "só pode criar empréstimos para si mesmo" in response.json()["detail"]


class TestMaxActiveLoansLimit:
    @pytest.mark.asyncio
    async def test_max_three_active_loans(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        books = [await create_book() for _ in range(4)]
        for i in range(3):
            response = await client.post(
                "/loans/",
                json={"user_id": authenticated_user.id, "book_id": books[i].id},
            )
            assert response.status_code == 201

        response = await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": books[3].id}
        )
        assert response.status_code == 400
        assert "atingiu o limite" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_can_loan_after_return(
        self, client: AsyncClient, authenticated_user, create_book
    ):
        books = [await create_book() for _ in range(4)]
        loan_ids = []
        for i in range(3):
            response = await client.post(
                "/loans/",
                json={"user_id": authenticated_user.id, "book_id": books[i].id},
            )
            loan_ids.append(response.json()["id"])

        await client.post(f"/loans/{loan_ids[0]}/return")

        response = await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": books[3].id}
        )
        assert response.status_code == 201


class TestBlockLoanIfOverdue:
    @pytest.mark.asyncio
    async def test_block_new_loan_if_user_has_overdue(
        self,
        client: AsyncClient,
        authenticated_user,
        create_book,
        db_session: AsyncSession,
    ):
        books = [await create_book() for _ in range(2)]
        overdue_loan = OverdueLoanFactory.build(
            user_id=authenticated_user.id, book_id=books[0].id
        )
        db_session.add(overdue_loan)
        await db_session.commit()

        response = await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": books[1].id}
        )
        assert response.status_code == 400
        assert "atrasados pendentes" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_allow_loan_if_no_overdue(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        books = [await create_book() for _ in range(2)]
        await create_loan(
            user_id=authenticated_user.id,
            book_id=books[0].id,
            expected_return_date=datetime.now(timezone.utc) + timedelta(days=7),
        )

        response = await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": books[1].id}
        )
        assert response.status_code == 201


class TestReturnLoan:
    @pytest.mark.asyncio
    async def test_return_loan_success(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        book = await create_book(available_copies=4)
        loan = await create_loan(user_id=authenticated_user.id, book_id=book.id)
        response = await client.post(f"/loans/{loan.id}/return")
        assert response.status_code == 200
        assert response.json()["message"] == "Livro retornado."

    @pytest.mark.asyncio
    async def test_return_loan_increments_available_copies(
        self,
        client: AsyncClient,
        authenticated_user,
        create_book,
        create_loan,
        db_session: AsyncSession,
    ):
        book = await create_book(available_copies=4)
        loan = await create_loan(user_id=authenticated_user.id, book_id=book.id)
        await client.post(f"/loans/{loan.id}/return")
        await db_session.refresh(book)
        assert book.available_copies == 5

    @pytest.mark.asyncio
    async def test_return_loan_not_found(self, client: AsyncClient):
        response = await client.post("/loans/99999/return")
        assert response.status_code == 404
        assert "Empréstimo não encontrado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_return_already_returned_loan(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        book = await create_book()
        loan = await create_loan(user_id=authenticated_user.id, book_id=book.id)
        await client.post(f"/loans/{loan.id}/return")
        response = await client.post(f"/loans/{loan.id}/return")
        assert response.status_code == 400
        assert "Empréstimo já devolvido" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_return_other_users_loan_forbidden(
        self, client: AsyncClient, create_book, create_user, create_loan
    ):
        book = await create_book()
        other_user = await create_user(email="returnother@user.com")
        loan = await create_loan(user_id=other_user.id, book_id=book.id)
        response = await client.post(f"/loans/{loan.id}/return")
        assert response.status_code == 403


class TestReturnLoanWithFine:
    @pytest.mark.asyncio
    async def test_return_overdue_loan_calculates_fine(
        self,
        client: AsyncClient,
        authenticated_user,
        create_book,
        db_session: AsyncSession,
    ):
        book = await create_book()
        now = datetime.now(timezone.utc)
        loan = LoanFactory.build(
            user_id=authenticated_user.id,
            book_id=book.id,
            loan_date=now - timedelta(days=19),
            expected_return_date=now - timedelta(days=5),
            status=LoanStatus.ACTIVE,
        )
        db_session.add(loan)
        await db_session.commit()
        await db_session.refresh(loan)

        response = await client.post(f"/loans/{loan.id}/return")
        assert response.status_code == 200
        data = response.json()
        assert data["days_overdue"] == 5
        assert data["fine_amount"] == "R$ 10.00"

    @pytest.mark.asyncio
    async def test_return_on_time_no_fine(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        book = await create_book()
        now = datetime.now(timezone.utc)
        loan = await create_loan(
            user_id=authenticated_user.id,
            book_id=book.id,
            loan_date=now - timedelta(days=7),
            expected_return_date=now + timedelta(days=7),
        )

        response = await client.post(f"/loans/{loan.id}/return")
        assert response.status_code == 200
        data = response.json()
        assert data.get("days_overdue", 0) == 0

    @pytest.mark.asyncio
    async def test_fine_calculation_one_day_overdue(
        self,
        client: AsyncClient,
        authenticated_user,
        create_book,
        db_session: AsyncSession,
    ):
        book = await create_book()
        now = datetime.now(timezone.utc)
        loan = LoanFactory.build(
            user_id=authenticated_user.id,
            book_id=book.id,
            loan_date=now - timedelta(days=15),
            expected_return_date=now - timedelta(days=1),
            status=LoanStatus.ACTIVE,
        )
        db_session.add(loan)
        await db_session.commit()
        await db_session.refresh(loan)

        response = await client.post(f"/loans/{loan.id}/return")
        assert response.status_code == 200
        data = response.json()
        assert data["days_overdue"] == 1
        assert data["fine_amount"] == "R$ 2.00"


class TestListLoans:
    @pytest.fixture
    async def loans_setup(
        self, db_session: AsyncSession, authenticated_user, create_book
    ):
        book1 = await create_book()
        book2 = await create_book()

        now = datetime.now(timezone.utc)
        active_loan = LoanFactory.build(user_id=authenticated_user.id, book_id=book1.id)
        returned_loan = LoanFactory.build(
            user_id=authenticated_user.id,
            book_id=book2.id,
            loan_date=now - timedelta(days=20),
            expected_return_date=now - timedelta(days=6),
            return_date=now - timedelta(days=5),
            status=LoanStatus.RETURNED,
        )
        db_session.add_all([active_loan, returned_loan])
        await db_session.commit()
        await db_session.refresh(active_loan)
        await db_session.refresh(returned_loan)
        return {"active": active_loan, "returned": returned_loan}

    @pytest.mark.asyncio
    async def test_list_all_loans(
        self, client: AsyncClient, loans_setup, authenticated_user
    ):
        response = await client.get(f"/loans/?user_id={authenticated_user.id}")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_list_active_loans_only(
        self, client: AsyncClient, loans_setup, authenticated_user
    ):
        response = await client.get(
            f"/loans/?user_id={authenticated_user.id}&status={LoanStatus.ACTIVE.value}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == LoanStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_list_returned_loans_only(
        self, client: AsyncClient, loans_setup, authenticated_user
    ):
        response = await client.get(
            f"/loans/?user_id={authenticated_user.id}&status={LoanStatus.RETURNED.value}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == LoanStatus.RETURNED.value

    @pytest.mark.asyncio
    async def test_list_loans_pagination(
        self, client: AsyncClient, loans_setup, authenticated_user
    ):
        response = await client.get(
            f"/loans/?user_id={authenticated_user.id}&skip=0&limit=1"
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_list_loans_skip_beyond_total(
        self, client: AsyncClient, loans_setup, authenticated_user
    ):
        response = await client.get(f"/loans/?user_id={authenticated_user.id}&skip=100")
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_list_loans_only_own_loans(
        self, client: AsyncClient, loans_setup, create_user
    ):
        other_user = await create_user(email="otherloan@user.com")
        response = await client.get(f"/loans/?user_id={other_user.id}")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_list_loans_overdue_pagination(
        self,
        client: AsyncClient,
        authenticated_user,
        db_session: AsyncSession,
    ):

        book = BookFactory.build(total_copies=20, available_copies=20)
        db_session.add(book)
        await db_session.commit()
        await db_session.refresh(book)

        for _ in range(5):
            loan = LoanFactory.build(user_id=authenticated_user.id, book_id=book.id)
            db_session.add(loan)

        for _ in range(5):
            loan = OverdueLoanFactory.build(
                user_id=authenticated_user.id, book_id=book.id
            )
            db_session.add(loan)

        await db_session.commit()

        response = await client.get(
            f"/loans/?status={LoanStatus.OVERDUE.value}&limit=2&skip=0"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2, (
            f"Expected 2 overdue loans, got {len(data)}. Data: {data}"
        )

        for loan_data in data:
            assert loan_data["status"] == LoanStatus.OVERDUE.value


class TestLoanLifecycle:
    @pytest.mark.asyncio
    async def test_full_lifecycle(
        self,
        client: AsyncClient,
        authenticated_user,
        create_book,
        db_session: AsyncSession,
    ):
        book = await create_book(available_copies=2)

        loan_response = await client.post(
            "/loans/", json={"user_id": authenticated_user.id, "book_id": book.id}
        )
        assert loan_response.status_code == 201
        loan_id = loan_response.json()["id"]
        assert loan_response.json()["status"] == LoanStatus.ACTIVE.value

        await db_session.refresh(book)
        assert book.available_copies == 1

        return_response = await client.post(f"/loans/{loan_id}/return")
        assert return_response.status_code == 200

        await db_session.refresh(book)
        assert book.available_copies == 2

        list_active = await client.get(
            f"/loans/?user_id={authenticated_user.id}&status={LoanStatus.ACTIVE.value}"
        )
        assert len(list_active.json()) == 0

        list_returned = await client.get(
            f"/loans/?user_id={authenticated_user.id}&status={LoanStatus.RETURNED.value}"
        )
        assert len(list_returned.json()) == 1
        assert list_returned.json()[0]["id"] == loan_id


class TestLoanAuthentication:
    @pytest.mark.asyncio
    async def test_create_loan_requires_authentication(
        self, client_unauthenticated: AsyncClient, create_book
    ):
        book = await create_book()
        response = await client_unauthenticated.post(
            "/loans/", json={"user_id": 1, "book_id": book.id}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_return_loan_requires_authentication(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.post("/loans/1/return")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_loans_requires_authentication(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get("/loans/")
        assert response.status_code == 401


class TestConcurrentLoans:
    @pytest.mark.asyncio
    async def test_concurrent_loan_last_copy_pessimistic_lock(
        self,
        authenticated_user,
        create_book,
        db_session: AsyncSession,
        redis_client_test,
    ):
        book = await create_book(total_copies=1, available_copies=1)

        payload = {"user_id": authenticated_user.id, "book_id": book.id}

        session_factory = async_sessionmaker(
            bind=db_session.bind, class_=AsyncSession, expire_on_commit=False
        )

        async def override_get_db():
            async with session_factory() as session:
                yield session

        async def override_get_redis():
            yield redis_client_test

        async def override_get_current_user():
            return authenticated_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_redis] = override_get_redis
        app.dependency_overrides[get_current_user] = override_get_current_user

        async def make_request(client: AsyncClient):
            return await client.post("/loans/", json=payload)

        try:
            async with (
                AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c1,
                AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c2,
            ):
                responses = await asyncio.gather(make_request(c1), make_request(c2))
        finally:
            app.dependency_overrides.clear()
        status_codes = sorted([r.status_code for r in responses])
        assert status_codes == [201, 400]
        assert any(
            "Livro não disponível" in r.json().get("detail", "")
            for r in responses
            if r.status_code == 400
        )

        await db_session.refresh(book)
        assert book.available_copies == 0

        result = await db_session.execute(
            select(func.count(Loan.id)).where(Loan.book_id == book.id)
        )
        assert result.scalar() == 1


class TestExportLoansCSV:
    @pytest.mark.asyncio
    async def test_export_loans_csv_success(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        """Testa exportação de CSV com empréstimos."""
        book = await create_book()
        loan = await create_loan(authenticated_user.id, book.id)

        response = await client.get("/loans/export/csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "emprestimos.csv" in response.headers["content-disposition"]

        csv_content = response.text
        assert "ID" in csv_content
        assert "Usuário (ID)" in csv_content
        assert "Livro (ID)" in csv_content
        assert "Título do Livro" in csv_content
        assert "Nome do Usuário" in csv_content
        assert "Data do Empréstimo" in csv_content
        assert "Data Esperada de Devolução" in csv_content
        assert "Status" in csv_content
        assert "Multa (R$)" in csv_content

    @pytest.mark.asyncio
    async def test_export_loans_csv_includes_loan_data(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        """Testa se dados dos empréstimos aparecem no CSV."""
        book = await create_book(title="Clean Code", author="Robert Martin")
        loan = await create_loan(authenticated_user.id, book.id)

        response = await client.get("/loans/export/csv")

        assert response.status_code == 200
        csv_content = response.text

        assert str(loan.id) in csv_content
        assert str(authenticated_user.id) in csv_content
        assert str(book.id) in csv_content
        assert "Clean Code" in csv_content
        assert authenticated_user.name in csv_content
        assert "ACTIVE" in csv_content

    @pytest.mark.asyncio
    async def test_export_loans_csv_filters_by_user_id(
        self,
        client: AsyncClient,
        authenticated_user,
        create_user,
        create_book,
        create_loan,
        db_session: AsyncSession,
    ):
        """Testa filtro por user_id na exportação."""
        other_user = await create_user(email="other@test.com")
        book = await create_book()

        loan1 = await create_loan(authenticated_user.id, book.id)

        loan2 = await create_loan(other_user.id, book.id)

        response = await client.get("/loans/export/csv")

        assert response.status_code == 200
        csv_content = response.text

        assert str(loan1.id) in csv_content

        assert authenticated_user.name in csv_content
        assert other_user.name not in csv_content

    @pytest.mark.asyncio
    async def test_export_loans_csv_filters_by_status(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        """Testa filtro por status na exportação."""
        book = await create_book()

        active_loan = await create_loan(
            authenticated_user.id, book.id, status=LoanStatus.ACTIVE
        )

        returned_loan = await create_loan(
            authenticated_user.id,
            book.id,
            status=LoanStatus.RETURNED,
            return_date=datetime.now(timezone.utc),
        )

        response = await client.get("/loans/export/csv?status=ACTIVE")

        assert response.status_code == 200
        csv_content = response.text

        lines = csv_content.strip().split("\n")

        assert len(lines) == 2
        assert lines[1].startswith("1,")
        assert "ACTIVE" in csv_content
        assert "RETURNED" not in csv_content

    @pytest.mark.asyncio
    async def test_export_loans_csv_empty_result(
        self, client: AsyncClient, authenticated_user
    ):
        """Testa exportação quando não há empréstimos."""
        response = await client.get("/loans/export/csv")

        assert response.status_code == 200
        csv_content = response.text

        lines = csv_content.strip().split("\n")
        assert len(lines) == 1
        assert "ID" in csv_content

    @pytest.mark.asyncio
    async def test_export_loans_csv_with_fine_amount(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        """Testa se multa aparece corretamente no CSV."""
        book = await create_book()
        loan = await create_loan(
            authenticated_user.id,
            book.id,
            status=LoanStatus.RETURNED,
            fine_amount=Decimal("10.00"),
            return_date=datetime.now(timezone.utc),
        )

        response = await client.get("/loans/export/csv")

        assert response.status_code == 200
        csv_content = response.text

        assert "10.00" in csv_content

    @pytest.mark.asyncio
    async def test_export_loans_csv_requires_authentication(
        self, client_unauthenticated: AsyncClient
    ):
        """Testa se endpoint requer autenticação."""
        response = await client_unauthenticated.get("/loans/export/csv")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_loans_csv_multiple_loans(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        """Testa exportação com múltiplos empréstimos."""
        book1 = await create_book(title="Book 1")
        book2 = await create_book(title="Book 2")
        book3 = await create_book(title="Book 3")

        loan1 = await create_loan(authenticated_user.id, book1.id)
        loan2 = await create_loan(
            authenticated_user.id,
            book2.id,
            status=LoanStatus.RETURNED,
            return_date=datetime.now(timezone.utc),
        )
        loan3 = await create_loan(authenticated_user.id, book3.id)

        response = await client.get("/loans/export/csv")

        assert response.status_code == 200
        csv_content = response.text

        assert str(loan1.id) in csv_content
        assert str(loan2.id) in csv_content
        assert str(loan3.id) in csv_content
        assert "Book 1" in csv_content
        assert "Book 2" in csv_content
        assert "Book 3" in csv_content

    @pytest.mark.asyncio
    async def test_export_loans_csv_date_formatting(
        self, client: AsyncClient, authenticated_user, create_book, create_loan
    ):
        """Testa se datas são formatadas corretamente no CSV."""
        book = await create_book()
        loan = await create_loan(authenticated_user.id, book.id)

        response = await client.get("/loans/export/csv")

        assert response.status_code == 200
        csv_content = response.text

        assert "/" in csv_content
        assert ":" in csv_content
