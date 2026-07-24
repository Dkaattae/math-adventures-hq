"""Tiny in-process sliding-window rate limiter.

Per-process by design: the app ships as a single container, so a dict of
timestamps is enough. Behind multiple replicas each process keeps its own
window (so the effective limit multiplies by the replica count) — move
the counters to Redis or Postgres if it ever scales out.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Optional


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> Optional[int]:
        """Record an attempt for `key`.

        Returns None when it's allowed, or the seconds to wait before the
        oldest hit in the window falls out of it.
        """
        if self.limit <= 0:  # 0 disables the limiter entirely
            return None
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(1, int(self.window_seconds - (now - hits[0])) + 1)
        hits.append(now)
        return None

    def reset(self) -> None:
        self._hits.clear()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Signup is unauthenticated, so it's the endpoint someone would use to
# squat names or fill the users table. The default is generous enough for
# a family or a small classroom sharing one IP; raise SIGNUP_RATE_LIMIT
# for a bigger shared network, or set it to 0 to turn the limit off.
signup_limiter = SlidingWindowLimiter(
    limit=_env_int("SIGNUP_RATE_LIMIT", 10),
    window_seconds=_env_int("SIGNUP_RATE_WINDOW_SECONDS", 3600),
)


def client_key(request) -> str:
    """Best-effort client identity for rate limiting.

    X-Forwarded-For is trusted because the app runs behind a platform
    proxy (Railway/Fly/Render all set it); a client that reaches uvicorn
    directly could spoof it, which is why this is a speed bump rather
    than a security boundary.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
