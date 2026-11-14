"""User accounts stored in TigerDB (TEAM-PLAN A task 7, step 5; after the M2 full run).

Passwords are stored only as hashes (argon2 or bcrypt). Who logs in and whether login replaces
the per-call family link is still open question 8 in TEAM-PLAN.md.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/auth")


@router.post("/signup")
async def signup() -> dict:
    raise HTTPException(status_code=501, detail="not implemented yet")


@router.post("/login")
async def login() -> dict:
    raise HTTPException(status_code=501, detail="not implemented yet")


@router.post("/logout")
async def logout() -> dict:
    raise HTTPException(status_code=501, detail="not implemented yet")
