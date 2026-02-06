import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.loans.models import LoanStatus
from app.domains.users.schemas import UserRole
from tests.factories import OverdueLoanFactory


class TestCreateUser:
    @pytest.fixture
    def valid_user_data(self):
        return {
            "name": "Test User",
            "email": "testuser@example.com",
            "password": "securepass123",
        }

    @pytest.mark.asyncio
    async def test_create_user_success(self, client: AsyncClient, valid_user_data):
        response = await client.post("/users/", json=valid_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == valid_user_data["name"]
        assert data["email"] == valid_user_data["email"]
        assert data["role"] == UserRole.USER.value
        assert data["is_active"] is True
        assert data["must_reset_password"] is False
        assert "id" in data
        assert "created_at" in data
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, client: AsyncClient, valid_user_data
    ):
        await client.post("/users/", json=valid_user_data)
        response = await client.post("/users/", json=valid_user_data)
        assert response.status_code == 400
        assert "Email já registrado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_user_missing_name(self, client: AsyncClient):
        response = await client.post(
            "/users/", json={"email": "test@example.com", "password": "pass123456"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_missing_email(self, client: AsyncClient):
        response = await client.post(
            "/users/", json={"name": "Test User", "password": "pass123456"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_missing_password(self, client: AsyncClient):
        response = await client.post(
            "/users/", json={"name": "Test User", "email": "test@example.com"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_invalid_email_format(self, client: AsyncClient):
        response = await client.post(
            "/users/",
            json={
                "name": "Test User",
                "email": "invalid-email",
                "password": "pass123456",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_empty_name(self, client: AsyncClient):
        response = await client.post(
            "/users/",
            json={"name": "", "email": "test@example.com", "password": "pass123456"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_short_password(self, client: AsyncClient):
        response = await client.post(
            "/users/",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "12345",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_password_exactly_min_length(self, client: AsyncClient):
        response = await client.post(
            "/users/",
            json={
                "name": "Test User",
                "email": "minpass@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_user_email_case_insensitive(self, client: AsyncClient):
        data1 = {
            "name": "User One",
            "email": "Test@Example.com",
            "password": "pass123456",
        }
        data2 = {
            "name": "User Two",
            "email": "test@example.com",
            "password": "pass123456",
        }
        await client.post("/users/", json=data1)
        response = await client.post("/users/", json=data2)
        assert response.status_code in [201, 400]

    @pytest.mark.asyncio
    async def test_create_user_long_name(self, client: AsyncClient):
        response = await client.post(
            "/users/",
            json={
                "name": "A" * 500,
                "email": "longname@example.com",
                "password": "pass123456",
            },
        )
        assert response.status_code == 201


class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_success(self, client: AsyncClient, create_user):
        user = await create_user(name="Existing User", email="existing@example.com")
        response = await client.get(f"/users/{user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["name"] == user.name
        assert data["email"] == user.email
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client: AsyncClient):
        response = await client.get("/users/99999")
        assert response.status_code == 404
        assert "Usuário não localizado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_user_invalid_id_type(self, client: AsyncClient):
        response = await client.get("/users/abc")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_user_negative_id(self, client: AsyncClient):
        response = await client.get("/users/-1")
        assert response.status_code in [404, 422]

    @pytest.mark.asyncio
    async def test_get_user_includes_created_at(self, client: AsyncClient, create_user):
        user = await create_user(email="createdat@example.com")
        response = await client.get(f"/users/{user.id}")
        assert response.status_code == 200
        assert "created_at" in response.json()


class TestListUsers:
    @pytest.mark.asyncio
    async def test_list_users_includes_authenticated_user(
        self, client: AsyncClient, authenticated_user
    ):
        response = await client.get("/users/")
        assert response.status_code == 200
        emails = [u["email"] for u in response.json()]
        assert authenticated_user.email in emails

    @pytest.mark.asyncio
    async def test_list_users_default_pagination(
        self, client: AsyncClient, create_user
    ):
        for i in range(15):
            await create_user(email=f"user{i}@pagination.com")
        response = await client.get("/users/")
        assert response.status_code == 200
        assert len(response.json()) == 10

    @pytest.mark.asyncio
    async def test_list_users_custom_limit(self, client: AsyncClient, create_user):
        for i in range(15):
            await create_user(email=f"user{i}@limit.com")
        response = await client.get("/users/?limit=5")
        assert response.status_code == 200
        assert len(response.json()) == 5

    @pytest.mark.asyncio
    async def test_list_users_custom_skip(self, client: AsyncClient, create_user):
        for i in range(15):
            await create_user(email=f"user{i}@skip.com")
        response = await client.get("/users/?skip=10")
        assert response.status_code == 200
        assert len(response.json()) <= 6

    @pytest.mark.asyncio
    async def test_list_users_skip_and_limit(self, client: AsyncClient, create_user):
        for i in range(15):
            await create_user(email=f"user{i}@skipandlimit.com")
        response = await client.get("/users/?skip=5&limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_list_users_skip_beyond_total(self, client: AsyncClient, create_user):
        for i in range(15):
            await create_user(email=f"user{i}@beyond.com")
        response = await client.get("/users/?skip=100")
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_list_users_no_password_in_response(
        self, client: AsyncClient, create_user
    ):
        for i in range(5):
            await create_user(email=f"user{i}@nopass.com")
        response = await client.get("/users/")
        assert response.status_code == 200
        for user in response.json():
            assert "password" not in user
            assert "hashed_password" not in user


class TestUserAuthentication:
    @pytest.mark.asyncio
    async def test_list_users_requires_authentication(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get("/users/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_users_requires_admin_role(self, client_user: AsyncClient):
        response = await client_user.get("/users/")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_requires_authentication(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get("/users/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_requires_admin_role(self, client_user: AsyncClient):
        response = await client_user.get("/users/1")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_user_does_not_require_authentication(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.post(
            "/users/",
            json={
                "name": "Public User",
                "email": "public@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_user_requires_admin_role(self, client_user: AsyncClient):
        response = await client_user.post(
            "/users/",
            json={
                "name": "Non Admin",
                "email": "nonadmin@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 403


class TestListUserLoans:
    @pytest.mark.asyncio
    async def test_list_user_loans_success(
        self,
        client: AsyncClient,
        create_user,
        create_book,
        create_loan,
    ):
        user = await create_user(email="loans@example.com")
        other_user = await create_user(email="otherloans@example.com")
        book = await create_book()

        await create_loan(user_id=user.id, book_id=book.id)
        await create_loan(user_id=other_user.id, book_id=book.id)

        response = await client.get(f"/users/{user.id}/loans")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == user.id

    @pytest.mark.asyncio
    async def test_list_user_loans_status_filter(
        self,
        client: AsyncClient,
        create_user,
        create_book,
        create_loan,
        db_session: AsyncSession,
    ):
        user = await create_user(email="statusfilter@example.com")
        book = await create_book()

        await create_loan(user_id=user.id, book_id=book.id, status=LoanStatus.RETURNED)

        overdue_loan = OverdueLoanFactory.build(user_id=user.id, book_id=book.id)
        db_session.add(overdue_loan)
        await db_session.commit()

        response = await client.get(
            f"/users/{user.id}/loans?status={LoanStatus.OVERDUE.value}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == LoanStatus.OVERDUE.value

    @pytest.mark.asyncio
    async def test_list_user_loans_user_not_found(self, client: AsyncClient):
        response = await client.get("/users/99999/loans")
        assert response.status_code == 404
        assert "Usuário não localizado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_user_loans_requires_authentication(
        self,
        client_unauthenticated: AsyncClient,
        create_user,
    ):
        user = await create_user(email="noauthloans@example.com")
        response = await client_unauthenticated.get(f"/users/{user.id}/loans")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_user_loans_requires_admin_role(
        self, client_user: AsyncClient, create_user
    ):
        user = await create_user(email="forbiddenloans@example.com")
        response = await client_user.get(f"/users/{user.id}/loans")
        assert response.status_code == 403


class TestUserSelfEndpoints:
    @pytest.mark.asyncio
    async def test_get_me(self, client_user: AsyncClient, authenticated_member):
        response = await client_user.get("/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == authenticated_member.id
        assert data["email"] == authenticated_member.email

    @pytest.mark.asyncio
    async def test_reset_my_password(self, client_user: AsyncClient):
        response = await client_user.post(
            "/users/me/reset-password",
            json={"new_password": "newpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["must_reset_password"] is False
        assert data["password_reset_at"] is not None


class TestUserAdminActions:
    @pytest.mark.asyncio
    async def test_update_user_status(self, client: AsyncClient, create_user):
        user = await create_user(email="status@example.com")
        response = await client.patch(
            f"/users/{user.id}/status", json={"is_active": False}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_require_password_reset(self, client: AsyncClient, create_user):
        user = await create_user(email="reset@example.com")
        response = await client.post(f"/users/{user.id}/reset-password")
        assert response.status_code == 200
        data = response.json()
        assert data["must_reset_password"] is True
        assert data["password_reset_at"] is not None

    @pytest.mark.asyncio
    async def test_lookup_users(self, client: AsyncClient, create_user):
        await create_user(name="Alice Example", email="alice@example.com")
        await create_user(name="Bob Example", email="bob@example.com")
        response = await client.get("/users/lookup?q=alice")
        assert response.status_code == 200
        results = response.json()
        assert any(user["email"] == "alice@example.com" for user in results)

    @pytest.mark.asyncio
    async def test_lookup_users_by_ids(self, client: AsyncClient, create_user):
        user1 = await create_user(email="idlookup1@example.com")
        user2 = await create_user(email="idlookup2@example.com")
        response = await client.get(f"/users/lookup/ids?ids={user1.id}&ids={user2.id}")
        assert response.status_code == 200
        results = response.json()
        ids = {u["id"] for u in results}
        assert user1.id in ids
        assert user2.id in ids

    @pytest.mark.asyncio
    async def test_export_users_pdf_success(self, client: AsyncClient):
        response = await client.get("/users/export/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_export_users_pdf_requires_auth(
        self, client_unauthenticated: AsyncClient
    ):
        response = await client_unauthenticated.get("/users/export/pdf")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_users_pdf_requires_admin(self, client_user: AsyncClient):
        response = await client_user.get("/users/export/pdf")
        assert response.status_code == 403
