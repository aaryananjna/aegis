"""The FastAPI app. Run: uvicorn aegis_server.main:app --app-dir server --port 8000"""
from __future__ import annotations

from fastapi import FastAPI

from .routes import auth, captions_ws, events_ws, sessions

app = FastAPI(title="Aegis server")
app.include_router(sessions.router)
app.include_router(captions_ws.router)
app.include_router(events_ws.router)
app.include_router(auth.router)
