import os
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

from app.main import app
from app.core.base import Base, get_db
from app.core.cache.redis import get_redis
from app.domains.auth.dependencies import get_current_user
from app.domains.users.models import User
from app.domains.users.schemas import UserRole
from tests.factories import UserFactory, BookFactory, LoanFactory


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/libsys"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def redis_client_test() -> AsyncGenerator[Redis, None]:
    redis = Redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)
    await redis.flushdb()
    yield redis
    await redis.aclose()


@pytest.fixture(scope="function")
async def authenticated_user(db_session: AsyncSession) -> User:
    user = UserFactory.build(email="admin@test.com", role=UserRole.ADMIN.value)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def authenticated_member(db_session: AsyncSession) -> User:
    user = UserFactory.build(email="member@test.com", role=UserRole.USER.value)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def client(
    db_session: AsyncSession, redis_client_test: Redis, authenticated_user: User
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield redis_client_test

    async def override_get_current_user():
        return authenticated_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client_unauthenticated(
    db_session: AsyncSession, redis_client_test: Redis
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield redis_client_test

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client_user(
    db_session: AsyncSession, redis_client_test: Redis, authenticated_member: User
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield redis_client_test

    async def override_get_current_user():
        return authenticated_member

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def book_factory():
    return BookFactory


@pytest.fixture
def loan_factory():
    return LoanFactory


@pytest.fixture
async def create_user(db_session: AsyncSession):
    async def _create_user(**kwargs):
        user = UserFactory.build(**kwargs)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture
async def create_book(db_session: AsyncSession):
    async def _create_book(**kwargs):
        book = BookFactory.build(**kwargs)
        db_session.add(book)
        await db_session.commit()
        await db_session.refresh(book)
        return book

    return _create_book


@pytest.fixture
async def create_loan(db_session: AsyncSession):
    async def _create_loan(user_id: int, book_id: int, **kwargs):
        loan = LoanFactory.build(user_id=user_id, book_id=book_id, **kwargs)
        db_session.add(loan)
        await db_session.commit()
        await db_session.refresh(loan)
        return loan

    return _create_loan
