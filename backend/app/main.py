from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter

from app.api.routers import users, books, loans
from app.models import User, Book, Loan
from app.core.redis import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):

    await FastAPILimiter.init(redis_client)
    yield
    await redis_client.close()


app = FastAPI(
    title="LibSys - Sistema de Gerenciamento de Biblioteca Digital", lifespan=lifespan
)

app.include_router(users.router)
app.include_router(books.router)
app.include_router(loans.router)


@app.get("/")
async def root():
    return {"status": "online", "message": "LibSys API", "version": "1.0.0"}
