from fastapi import FastAPI

app = FastAPI(title="LibSys - Sistema de Gerenciamento de Biblioteca Digital")

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "LibSys API",
    }