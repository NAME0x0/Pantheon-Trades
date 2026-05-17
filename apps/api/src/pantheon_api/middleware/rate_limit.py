"""Global IP-keyed rate limiting via slowapi.

slowapi (https://github.com/laurentS/slowapi) wraps the ``limits``
library and integrates cleanly with FastAPI dependency injection.
We keep the existing address-keyed auth rate limiter (which guards
SIWE nonce abuse) and layer slowapi on top of *public* endpoints to
slow brute-force traversal of the catalog API.

Storage:
  - Redis backend when REDIS_URL is set (recommended for any
    multi-replica deployment).
  - In-memory fallback otherwise — fine for local dev / tests.

Defaults are intentionally generous; this is a backstop, not a
business-logic limit. Tighten per-route via ``@limiter.limit(...)``
on the relevant handler when needed.
"""

from __future__ import annotations

import os
from typing import Optional

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = structlog.get_logger("pantheon_api.rate_limit")

DEFAULT_LIMIT = os.environ.get("RATE_LIMIT_DEFAULT", "120/minute")
BURST_LIMIT = os.environ.get("RATE_LIMIT_BURST", "30/second")


def _build_limiter():
    """Build a slowapi ``Limiter`` instance.

    Returns ``None`` if slowapi is not installed — install_rate_limiting
    will then silently no-op. We never want a missing optional dep to
    crash the API.
    """
    try:
        from slowapi import Limiter
        from slowapi.util import get_remote_address
    except ImportError:
        return None

    redis_url = os.environ.get("REDIS_URL")
    storage_uri = redis_url if redis_url else "memory://"
    return Limiter(
        key_func=get_remote_address,
        default_limits=[DEFAULT_LIMIT, BURST_LIMIT],
        storage_uri=storage_uri,
        # ``headers_enabled`` adds X-RateLimit-* response headers so
        # clients can back off proactively before hitting 429.
        headers_enabled=True,
    )


limiter = _build_limiter()


def install_rate_limiting(app: FastAPI) -> None:
    """Wire slowapi into the given FastAPI app, if available."""
    if limiter is None:
        log.warning("pantheon_api.rate_limit.disabled_no_slowapi")
        return

    try:
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
    except ImportError:  # pragma: no cover — guarded by limiter check above
        return

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limited",
                "detail": (
                    "too many requests; back off and retry — see the "
                    "Retry-After header for the cooldown"
                ),
            },
            headers={"Retry-After": str(getattr(exc, "retry_after", 1) or 1)},
        )

    log.info(
        "pantheon_api.rate_limit.enabled",
        default=DEFAULT_LIMIT,
        burst=BURST_LIMIT,
        storage="redis" if os.environ.get("REDIS_URL") else "memory",
    )


def get_limiter() -> Optional[object]:
    """Module accessor — handlers can decorate ``@limiter.limit("X/min")``."""
    return limiter
