"""Who may call what.

"Laptop only" routes (POST /sessions, /sessions/{id}/end, /typed, WS /captions) have no token,
so they must only be reachable from the laptop itself. A loopback address alone isn't enough:
the family phone reaches the laptop through the Cloudflare tunnel and Vite's proxy, which both
connect from 127.0.0.1. Cloudflare adds forwarding headers, so a request that carries any of
them came from outside, even if it arrives on loopback.
"""
from __future__ import annotations

from starlette.requests import HTTPConnection

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
FORWARDED = ("x-forwarded-for", "forwarded", "x-real-ip", "cf-connecting-ip", "cf-ray",
             "x-forwarded-host", "true-client-ip")


def is_laptop(conn: HTTPConnection) -> bool:
    host = conn.client.host if conn.client else None
    if host not in LOOPBACK:
        return False
    return not any(h in conn.headers for h in FORWARDED)
