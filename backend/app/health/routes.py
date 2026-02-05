from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from redis.asyncio import Redis
from redis.exceptions import RedisError
import structlog

from app.core.base import get_db
from app.core.cache.redis import get_redis
from app.core.messages import ErrorMessages

router = APIRouter(tags=["Health"])
logger = structlog.get_logger()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)
):
    """
    Verifica a saúde das dependências vitais (DB e Cache).
    Retorna 503 se alguma falhar.
    """
    health_status = {"status": "ok", "postgres": "unknown", "redis": "unknown"}

    # 1. Check Postgres
    try:
        await db.execute(text("SELECT 1"))
        health_status["postgres"] = "ok"
    except SQLAlchemyError as e:
        health_status["postgres"] = "error"
        health_status["status"] = "error"
        logger.error(ErrorMessages.HEALTH_POSTGRES_ERROR, error=str(e))

    # 2. Check Redis
    try:
        await redis.ping()  # type: ignore
        health_status["redis"] = "ok"
    except RedisError as e:
        health_status["redis"] = "error"
        health_status["status"] = "error"
        logger.error(ErrorMessages.HEALTH_REDIS_ERROR, error=str(e))

    return health_status
