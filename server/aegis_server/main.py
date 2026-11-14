"""The FastAPI app. Run: uvicorn aegis_server.main:app --app-dir server --port 8000

Security that applies to every route:
- Tokens never reach a log: `token=` in any logged URL is replaced with `token=***`.
- Response headers: no caching, no sniffing, no framing, no Referer (the elder and family
  links carry tokens).
- CORS only for WEB_BASE_URL. API docs (/docs, /openapi.json) are off unless API_DOCS=1.
- On shutdown every live call is ended, so the mic stops and nothing is left in memory.
"""
from __future__ import annotations

import asyncio
import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import settings
from .routes import auth, captions_ws, elders, events_ws, sessions
from .sessions import store

log = logging.getLogger("aegis")

_SECRET = re.compile(r"(token=)[^&\s\"']+", re.I)


class RedactTokens(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SECRET.sub(r"\1***", record.msg)
        if record.args:
            args = record.args if isinstance(record.args, tuple) else (record.args,)
            record.args = tuple(_SECRET.sub(r"\1***", a) if isinstance(a, str) else a
                                for a in args)
        return True


for name in ("uvicorn.access", "uvicorn.error", "uvicorn"):
    logging.getLogger(name).addFilter(RedactTokens())


@asynccontextmanager
async def lifespan(app: FastAPI):
    for name in ("uvicorn.access", "uvicorn.error"):  # uvicorn may replace loggers at startup
        logging.getLogger(name).addFilter(RedactTokens())
    try:
        # Tests point the pool at a throwaway schema through app.state.db_server_settings.
        await db.connect(settings.tiger_database_url,
                         getattr(app.state, "db_server_settings", None))
    except Exception as e:  # live calls still work without the accounts database
        log.warning("accounts database unavailable: %s", type(e).__name__)
    yield
    await store.close_all()
    await asyncio.sleep(0.2)  # let call_ended reach the screens
    await db.close()


app = FastAPI(title="Aegis server", lifespan=lifespan,
              docs_url="/docs" if settings.docs else None, redoc_url=None,
              openapi_url="/openapi.json" if settings.docs else None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    h = response.headers
    h.setdefault("Cache-Control", "no-store")
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "no-referrer")
    h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    return response


# C's screens run on another port; they send the login cookie with credentials: "include".
app.add_middleware(CORSMiddleware, allow_origins=[settings.web_base_url],
                   allow_credentials=True, allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Content-Type", "Authorization", "X-Device-Token"])
app.include_router(sessions.router)
app.include_router(captions_ws.router)
app.include_router(events_ws.router)
app.include_router(auth.router)
app.include_router(elders.router)
