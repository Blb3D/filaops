# path: backend/app/core/limiter.py
"""
Optional rate limiting support.
- If 'slowapi' is installed, a real Limiter is provided and middleware/handlers are applied.
- If not installed, exposes a no-op limiter so decorated routes still work without crashes.
"""

from typing import Tuple

# Try SlowAPI imports. If missing, we fall back to a no-op limiter.
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    from slowapi.middleware import SlowAPIMiddleware  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore

    HAS_SLOWAPI = True
except Exception:
    Limiter = None  # type: ignore
    _rate_limit_exceeded_handler = None  # type: ignore
    RateLimitExceeded = Exception  # type: ignore
    SlowAPIMiddleware = None  # type: ignore
    get_remote_address = None  # type: ignore
    HAS_SLOWAPI = False


class _NoopLimiter:
    """Why: allow @limiter.limit(...) decorators to be present with zero effect when slowapi isn't installed."""

    def limit(self, *_args, **_kwargs):
        def decorator(fn):
            return fn

        return decorator


# Expose a module-level limiter for decorators at import time.
# If SlowAPI is available, create a real Limiter; otherwise no-op.
if HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address)  # type: ignore
else:
    limiter = _NoopLimiter()


def apply_rate_limiting(app) -> Tuple[object, bool]:
    """
    Attach SlowAPI middleware and exception handler if available.
    Returns (limiter, enabled_flag).
    """
    if not HAS_SLOWAPI or _rate_limit_exceeded_handler is None or SlowAPIMiddleware is None:
        # No slowapi installed: leave limiter as no-op and do nothing.
        app.state.limiter = limiter
        return limiter, False

    # Attach real limiter to app and wire middleware/handler.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)  # type: ignore[arg-type]
    return limiter, True
