"""Small in-process sliding-window rate limiter for login and QR check-in.

Good enough for the single-instance deployment in the scope; Nginx
``limit_req`` (see deploy/nginx.conf) adds a second layer in production.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.common.config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window: int) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                retry = int(window - (now - q[0])) + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please try again shortly.",
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    """The peer address. Behind Nginx, uvicorn's ``--proxy-headers`` already
    replaces it with the real client IP from a trusted proxy; the raw
    X-Forwarded-For header is never read here because clients can forge it."""
    return request.client.host if request.client else "unknown"


def login_rate_limit(request: Request) -> None:
    s = get_settings()
    if s.rate_limit_enabled:
        limiter.check(f"login:{client_ip(request)}", s.login_rate_limit, s.login_rate_window_seconds)


def checkin_rate_limit(request: Request) -> None:
    s = get_settings()
    if s.rate_limit_enabled:
        limiter.check(f"checkin:{client_ip(request)}", s.checkin_rate_limit, s.checkin_rate_window_seconds)


def kiosk_rate_limit(request: Request) -> None:
    s = get_settings()
    if s.rate_limit_enabled:
        # A display polls about once a minute; allow generous headroom.
        limiter.check(f"kiosk:{client_ip(request)}", 30, 60)
