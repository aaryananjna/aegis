"""In-memory sliding-window limits for login and signup.

Memory only, per server process: a restart clears them. Enough for one demo server; a
multi-process deployment would need a shared store.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque


class Limiter:
    def __init__(self, limit: int, window_s: float) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._hits[key]
        while q and q[0] <= now - self.window_s:
            q.popleft()
        return q

    def retry_after(self, key: str, now: float | None = None) -> int:
        """Seconds until `key` may try again; 0 means it isn't blocked."""
        now = time.monotonic() if now is None else now
        q = self._prune(key, now)
        if len(q) < self.limit:
            if not q:
                del self._hits[key]  # keep the dict from growing with one-off keys
            return 0
        return max(1, int(q[0] + self.window_s - now + 0.999))

    def hit(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def clear(self) -> None:
        self._hits.clear()


# Failed logins per email, failed logins per client address, signups per client address.
login_by_email = Limiter(limit=5, window_s=15 * 60)
login_by_ip = Limiter(limit=20, window_s=15 * 60)
signup_by_ip = Limiter(limit=10, window_s=60 * 60)


def clear_all() -> None:
    for lim in (login_by_email, login_by_ip, signup_by_ip):
        lim.clear()
