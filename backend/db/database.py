import os
import sys
from contextlib import asynccontextmanager
import asyncpg
from typing import AsyncGenerator

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL no está configurado.", file=sys.stderr)
    sys.exit(1)

_pool: asyncpg.Pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def get_conn_with_tenant(tenant_id: int) -> AsyncGenerator[asyncpg.Connection, None]:
    """Get connection with tenant context set for RLS."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"SET app.current_tenant = '{tenant_id}'")
        yield conn


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_pool():
    """Inicializar el pool de conexiones al arrancar la app."""
    await get_pool()


async def shutdown_pool():
    """Cerrar el pool de conexiones al apagar la app."""
    await close_pool()
