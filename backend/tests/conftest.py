import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

from app.main import app
from app.db.base import Base, get_db
from app.core.config import settings
from app.core.redis import get_redis

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine_test, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="function")
async def redis_client_test():
    """
    Cria uma conexão Redis isolada para o Event Loop do teste atual.
    """
    redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    await FastAPILimiter.init(redis)

    await redis.flushdb()

    yield redis

    await redis.aclose()


@pytest.fixture(scope="function")
async def db_session():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session, redis_client_test) -> AsyncGenerator[AsyncClient, None]:
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
