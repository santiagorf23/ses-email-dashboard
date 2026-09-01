import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import emails, auth
from db.database import init_pool, shutdown_pool
import uvicorn

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SES Mail Dashboard", version="1.0.0")

# CORS restrictivo — solo orígenes permitidos
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:8088").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(emails.router, prefix="/api/emails", tags=["emails"])


@app.on_event("startup")
async def startup():
    logger.info("Iniciando SES Mail Dashboard...")
    await init_pool()
    logger.info("Pool de conexiones inicializado")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Apagando SES Mail Dashboard...")
    await shutdown_pool()
    logger.info("Pool de conexiones cerrado")


@app.get("/api/health")
async def health():
    from db.database import get_pool
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error("Health check falló: %s", e)
        return {"status": "degraded", "database": "disconnected", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)