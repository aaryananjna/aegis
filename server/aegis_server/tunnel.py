"""The Cloudflare quick tunnel's public address, so the family link works on a phone.

`cloudflared tunnel --url http://localhost:5173` prints a random https://<words>.trycloudflare.com
address, and also serves it on its local status page (127.0.0.1:20241-20245/quicktunnel). When
a tunnel is running, family links use that address; elder links stay on localhost, because the
grandparent's screen is this laptop.

TUNNEL_URL in server/.env fixes the address by hand; TUNNEL_URL=off turns this off.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import urllib.request

PORTS = range(20241, 20246)  # where cloudflared puts its status page
_HOST = re.compile(r"^[a-z0-9-]+\.trycloudflare\.com$")
_cache: tuple[float, str | None] = (0.0, None)


def _ask_cloudflared() -> str | None:
    for port in PORTS:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/quicktunnel", timeout=0.3) as r:
                host = json.load(r).get("hostname", "")
        except Exception:
            continue
        if _HOST.match(host or ""):
            return f"https://{host}"
    return None


async def public_origin() -> str | None:
    """https://<tunnel> if a quick tunnel is running (checked at most every 10 s), else None."""
    global _cache
    fixed = os.getenv("TUNNEL_URL", "").strip()
    if fixed.lower() == "off":
        return None
    if fixed:
        return fixed.rstrip("/")
    seen, origin = _cache
    if time.monotonic() - seen < 10:
        return origin
    origin = await asyncio.to_thread(_ask_cloudflared)
    _cache = (time.monotonic(), origin)
    return origin
