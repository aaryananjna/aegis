"""Settings read from server/.env. Keys never leave the server and are never logged."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")
    tiger_database_url: str = os.getenv("TIGER_DATABASE_URL", "")
    web_base_url: str = os.getenv("WEB_BASE_URL", "http://localhost:5173")
    tick_s: float = 1.0  # detector tick, even in silence (CONTRACTS: caption section)


settings = Settings()
