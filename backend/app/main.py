from fastapi import FastAPI
from app.api.routers import users, books, loans

from app.models import User, Book, Loan

app = FastAPI(title="LibSys - Sistema de Gerenciamento de Biblioteca Digital")

app.include_router(users.router)
app.include_router(books.router)
app.include_router(loans.router)

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "LibSys API",
        "version": "1.0.0"
    }