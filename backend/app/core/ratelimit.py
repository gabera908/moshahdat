"""Tiny in-memory sliding-window rate limiter for sensitive routes.

Suitable for single-instance MVP deployments behind nginx; swap for Redis
when scaling horizontally.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit_per_minute: int) -> None:
        """Raise 429 when the caller exceeds `limit_per_minute`."""
        now = time.monotonic()
        window_start = now - 60.0
        with self._lock:
            dq = self._hits[key]
            while dq and dq[0] < window_start:
                dq.popleft()
            if len(dq) >= limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="عدد كبير من المحاولات. حاول بعد قليل.",
                )
            dq.append(now)
            # Opportunistic cleanup to keep memory bounded.
            if len(self._hits) > 10_000:
                stale = [k for k, v in self._hits.items() if not v or v[-1] < window_start]
                for k in stale[:5000]:
                    self._hits.pop(k, None)


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    """Extract the caller IP, honoring X-Forwarded-For from trusted proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request, bucket: str, per_minute: int) -> None:
    limiter.check(f"{bucket}:{client_ip(request)}", per_minute)
