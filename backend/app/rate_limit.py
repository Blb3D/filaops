# file: backend/app/rate_limit.py
# why: make rate limiting optional; no crash if slowapi isn't installed
from typing import Optional

class _NoopLimiter:
    def limit(self, *_args, **_kwargs):
        def deco(fn):  # no-op decorator so routes still work
            return fn
        return deco

def setup_rate_limit(app) -> tuple[object, bool]:
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded

        # In-memory by default; for prod use Redis via storage_uri
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        return limiter, True
    except Exception:
        limiter = _NoopLimiter()
        return limiter, False
