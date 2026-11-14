"""TigerDB connection pool. Connection string from TIGER_DATABASE_URL in server/.env.

Holds login info, who watches whom and per-call numbers. Never audio, caption text or the
family code word. If TIGER_DATABASE_URL is empty the server still runs (live calls work);
only the account endpoints answer 503.
"""
from __future__ import annotations

import asyncpg
from fastapi import HTTPException

_pool: asyncpg.Pool | None = None


async def connect(dsn: str, server_settings: dict[str, str] | None = None) -> None:
    """Open the pool. Called once at startup (and by tests with their own schema)."""
    global _pool
    if _pool is None and dsn:
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5, timeout=15,
                                          command_timeout=10, server_settings=server_settings)


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    """The open pool, or 503 when the database isn't configured or reachable."""
    if _pool is None:
        raise HTTPException(status_code=503, detail="accounts database is not available")
    return _pool
