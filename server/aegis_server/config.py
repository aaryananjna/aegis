"""Settings read from server/.env. Keys never leave the server and are never logged."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Every outbound HTTPS call (Deepgram, and the AI layer's urllib calls to Groq and Gemini)
# checks certificates against certifi. python.org builds on macOS ship without system roots.
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")
    tiger_database_url: str = os.getenv("TIGER_DATABASE_URL", "")
    web_base_url: str = os.getenv("WEB_BASE_URL", "http://localhost:5173")
    tick_s: float = 1.0  # detector tick, even in silence (CONTRACTS: caption section)
    login_days: int = int(os.getenv("LOGIN_DAYS", "7"))  # how long a family login lasts
    # Set COOKIE_SECURE=1 when the server is served over https (not needed on localhost).
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "") == "1"
    docs: bool = os.getenv("API_DOCS", "") == "1"  # /docs and /openapi.json, off by default
    # The mic to use when a call doesn't name one (the website's Start button doesn't). Pin it
    # so an iPhone (Continuity) or AirPods taking over as the Mac's default input can't silently
    # swap the mic mid-demo. Empty = the Mac's default input.
    mic_device: str = os.getenv("MIC_DEVICE", "").strip()


settings = Settings()
