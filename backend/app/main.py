import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi_limiter import FastAPILimiter

from app.api.routers import users, books, loans, health
from app.core.redis import redis_client
from app.core.logs import configure_logging

configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", message="Initializing application services")
    await FastAPILimiter.init(redis_client)
    yield

    await redis_client.close()
    logger.info("shutdown", message="Application stopped")


app = FastAPI(
    title="LibSys - Sistema de Gerenciamento de Biblioteca Digital", lifespan=lifespan
)


@app.middleware("http")
async def structlog_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "unknown")
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id, method=request.method, path=request.url.path
    )

    start_time = time.perf_counter_ns()

    try:
        response = await call_next(request)
        process_time = time.perf_counter_ns() - start_time

        logger.info(
            "request_processed",
            status_code=response.status_code,
            latency_ms=process_time / 1_000_000,
        )
        return response
    except Exception as e:
        logger.error("request_failed", error=str(e))
        raise e


app.include_router(users.router)
app.include_router(books.router)
app.include_router(loans.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {"status": "online", "service": "LibSys API", "version": "1.0.0","docs": "/docs"}
