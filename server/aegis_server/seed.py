"""Seed demo accounts with made-up names. Safe to run twice.

Run (from server/):  python -m aegis_server.seed

Needs DEMO_PASSWORD in server/.env (the password both demo family accounts get). Creates:
  sam.rivera@example.com  (owner)  and  jo.rivera@example.com  (viewer), watching "Grandma Rose".
Prints a pairing link for the demo grandparent's laptop. The link holds a device token, so treat
it like a password and don't paste it anywhere public.
"""
from __future__ import annotations

import asyncio
import os

import asyncpg

from .config import settings
from .security import hash_password, new_token, token_hash

FAMILY = [("sam.rivera@example.com", "Sam Rivera", "owner"),
          ("jo.rivera@example.com", "Jo Rivera", "viewer")]
ELDER = "Grandma Rose"


async def seed() -> str:
    password = os.getenv("DEMO_PASSWORD", "")
    if len(password) < 8:
        raise SystemExit("set DEMO_PASSWORD (8+ characters) in server/.env first")
    if not settings.tiger_database_url:
        raise SystemExit("TIGER_DATABASE_URL is not set in server/.env")
    conn = await asyncpg.connect(settings.tiger_database_url, timeout=15)
    try:
        async with conn.transaction():
            owner_id = None
            elder_id = await conn.fetchval(
                "SELECT e.id FROM elders e JOIN elder_members m ON m.elder_id = e.id "
                "JOIN users u ON u.id = m.user_id "
                "WHERE e.display_name = $1 AND u.email = $2 AND m.role = 'owner'",
                ELDER, FAMILY[0][0])
            if elder_id is None:
                elder_id = await conn.fetchval(
                    "INSERT INTO elders (display_name) VALUES ($1) RETURNING id", ELDER)
            for email, name, role in FAMILY:
                uid = await conn.fetchval(
                    "INSERT INTO users (email, password_hash, display_name) VALUES ($1, $2, $3) "
                    "ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash "
                    "RETURNING id", email, hash_password(password), name)
                await conn.execute(
                    "INSERT INTO elder_members (elder_id, user_id, role) VALUES ($1, $2, $3) "
                    "ON CONFLICT DO NOTHING", elder_id, uid, role)
                owner_id = owner_id or uid
            token = new_token()
            await conn.execute("INSERT INTO elder_devices (token_hash, elder_id) VALUES ($1, $2)",
                               token_hash(token), elder_id)
    finally:
        await conn.close()
    return f"{settings.web_base_url}/pair#{token}"


def main() -> None:
    url = asyncio.run(seed())
    print("seeded Sam Rivera (owner) and Jo Rivera (viewer) watching Grandma Rose")
    print(f"open this once on the grandparent's laptop: {url}")


if __name__ == "__main__":
    main()
