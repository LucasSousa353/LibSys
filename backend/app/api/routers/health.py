from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis
import structlog

from app.db.base import get_db
from app.core.redis import get_redis

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
    except Exception as e:
        health_status["postgres"] = "error"
        health_status["status"] = "error"
        logger.error("Health check failed for Postgres", error=str(e))

    # toDo arrumar type
    # 2. Check Redis
    try:
        await redis.ping() # type: ignore
        health_status["redis"] = "ok"
    except Exception as e:
        health_status["redis"] = "error"
        health_status["status"] = "error"
        logger.error("Health check failed for Redis", error=str(e))

    return health_status
