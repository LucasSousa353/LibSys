import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter

from app.api.v1.routers import auth as auth_routes
from app.api.v1.routers import users as users_routes
from app.api.v1.routers import books as books_routes
from app.api.v1.routers import loans as loans_routes
from app.api.v1.routers import analytics as analytics_routes
from app.api.v1.routers import notifications as notifications_routes
from app.health.routes import router as health_router
from app.core.cache.redis import redis_client
from app.core.logging.config import configure_logging
from app.domains.audit import models as audit_models  # noqa: F401
from app.domains.notifications import models as notification_models  # noqa: F401

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


app.include_router(auth_routes.router)
app.include_router(users_routes.router)
app.include_router(books_routes.router)
app.include_router(loans_routes.router)
app.include_router(analytics_routes.router)
app.include_router(notifications_routes.router)
app.include_router(health_router)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "LibSys API",
        "version": "1.0.0",
        "docs": "/docs",
    }
