"""Database pool management using asyncpg."""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import asyncpg
from fastapi import Depends

from .config import settings


pool: asyncpg.Pool | None = None


async def get_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(settings.DATABASE_URL)
    try:
        yield pool
    finally:
        pass


async def init_db() -> None:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(settings.DATABASE_URL)
    # create schema if not exists
    import pathlib

    sql_file = pathlib.Path(__file__).resolve().parents[1] / "schema.sql"
    sql = sql_file.read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)


async def close_db() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None
