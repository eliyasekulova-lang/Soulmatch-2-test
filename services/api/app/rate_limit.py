import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from .settings import get_settings

settings = get_settings()

class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.time()
        boundary = now - window_seconds
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < boundary:
                bucket.popleft()
            if len(bucket) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="rate_limited",
                )
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = InMemoryRateLimiter()


def limit_auth_requests(request: Request) -> None:
    key = f"auth:{request.client.host if request.client else 'unknown'}"
    rate_limiter.check(key=key, max_requests=settings.auth_rate_limit_per_minute, window_seconds=60)


def limit_rights_requests(request: Request) -> None:
    key = f"rights:{request.client.host if request.client else 'unknown'}"
    rate_limiter.check(key=key, max_requests=10, window_seconds=60)


def limit_auth_identity_requests(ip: str, identity: str) -> None:
    normalized = identity.strip().lower()
    key = f"auth_identity:{ip}:{normalized}"
    rate_limiter.check(key=key, max_requests=12, window_seconds=60)


def limit_refresh_requests(request: Request) -> None:
    key = f"refresh:{request.client.host if request.client else 'unknown'}"
    rate_limiter.check(key=key, max_requests=settings.auth_refresh_rate_limit_per_minute, window_seconds=60)
