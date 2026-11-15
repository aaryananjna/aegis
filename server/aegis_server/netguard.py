"""Who may call what.

"Laptop only" routes (POST /sessions, /sessions/{id}/end, /typed, WS /captions) have no token,
so they must only be reachable from the laptop itself. A loopback address alone isn't enough:
the family phone reaches the laptop through the Cloudflare tunnel and Vite's proxy, which both
connect from 127.0.0.1. Cloudflare adds forwarding headers, so a request that carries any of
them came from outside, even if it arrives on loopback.

Browsers are the other way in: any website open on the laptop can send a request or open a
WebSocket to localhost. Browsers always say which site they're on (the Origin header), so a
browser request only counts as the laptop when it comes from our own site (WEB_BASE_URL).
Scripts like start-call and the Deepgram client send no Origin and are unaffected.
"""
from __future__ import annotations

from urllib.parse import urlparse

from starlette.requests import HTTPConnection

from .config import settings

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
FORWARDED = ("x-forwarded-for", "forwarded", "x-real-ip", "cf-connecting-ip", "cf-ray",
             "x-forwarded-host", "true-client-ip")


def _own_origins() -> set[str]:
    """WEB_BASE_URL, plus the same address spelled localhost / 127.0.0.1."""
    u = urlparse(settings.web_base_url)
    port = f":{u.port}" if u.port else ""
    out = {f"{u.scheme}://{u.hostname}{port}"}
    if u.hostname in LOOPBACK:
        out |= {f"{u.scheme}://{h}{port}" for h in ("localhost", "127.0.0.1", "[::1]")}
    return out


OWN_ORIGINS = _own_origins()


def from_own_site(conn: HTTPConnection) -> bool:
    origin = conn.headers.get("origin")
    return origin is None or origin.rstrip("/") in OWN_ORIGINS


def is_laptop(conn: HTTPConnection) -> bool:
    host = conn.client.host if conn.client else None
    if host not in LOOPBACK:
        return False
    if any(h in conn.headers for h in FORWARDED):
        return False
    return from_own_site(conn)
