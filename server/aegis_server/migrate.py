"""Apply server/migrations/*.sql to TigerDB, in order, each once.

Run:  python -m aegis_server.migrate            (from server/)
      python -m aegis_server.migrate --dry-run  (runs everything, then rolls back)

Applied files are recorded in schema_migrations. Each file runs in its own transaction.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import asyncpg

from .config import settings

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


class _DryRun(Exception):
    pass


async def migrate(dry_run: bool = False) -> list[str]:
    if not settings.tiger_database_url:
        raise SystemExit("TIGER_DATABASE_URL is not set in server/.env")
    conn = await asyncpg.connect(settings.tiger_database_url, timeout=15)
    applied: list[str] = []
    try:
        tx = conn.transaction()
        await tx.start()
        try:
            await conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                               "name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
            done = {r["name"] for r in await conn.fetch("SELECT name FROM schema_migrations")}
            for f in sorted(MIGRATIONS.glob("*.sql")):
                if f.name in done:
                    continue
                await conn.execute(f.read_text())
                await conn.execute("INSERT INTO schema_migrations (name) VALUES ($1)", f.name)
                applied.append(f.name)
            if dry_run:
                raise _DryRun
        except _DryRun:
            await tx.rollback()
            return applied
        except BaseException:
            await tx.rollback()
            raise
        await tx.commit()
    finally:
        await conn.close()
    return applied


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="run every new migration, then roll back")
    args = p.parse_args()
    names = asyncio.run(migrate(args.dry_run))
    verb = "would apply" if args.dry_run else "applied"
    print(f"{verb}: {', '.join(names) if names else 'nothing (up to date)'}")


if __name__ == "__main__":
    main()
