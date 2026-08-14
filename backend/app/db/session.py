"""Async database session/connection management (asyncpg)."""

import os

import asyncpg
from pgvector.asyncpg import register_vector

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the shared asyncpg connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, init=register_vector)
    return _pool


async def get_connection():
    """Acquire an asyncpg connection to the Postgres/pgvector database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
