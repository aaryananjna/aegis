"""TigerDB connection for user accounts (step 5). Connection string from TIGER_DATABASE_URL.

Holds login info only. Never audio, caption text or the family code word.
"""
from __future__ import annotations


async def connect() -> None:
    raise NotImplementedError


async def close() -> None:
    raise NotImplementedError
