"""The FastAPI app. Run: uvicorn aegis_server.main:app --app-dir server --port 8000"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import settings
from .routes import auth, captions_ws, elders, events_ws, sessions

log = logging.getLogger("aegis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Tests point the pool at a throwaway schema through app.state.db_server_settings.
        await db.connect(settings.tiger_database_url,
                         getattr(app.state, "db_server_settings", None))
    except Exception as e:  # live calls still work without the accounts database
        log.warning("accounts database unavailable: %s", type(e).__name__)
    yield
    await db.close()


app = FastAPI(title="Aegis server", lifespan=lifespan)
# C's screens run on another port; they send the login cookie with credentials: "include".
app.add_middleware(CORSMiddleware, allow_origins=[settings.web_base_url],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(sessions.router)
app.include_router(captions_ws.router)
app.include_router(events_ws.router)
app.include_router(auth.router)
app.include_router(elders.router)
