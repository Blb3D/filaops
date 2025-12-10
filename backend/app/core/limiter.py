"""
Rate limiter configuration - shared across all endpoints

This module initializes the rate limiter at import time so it can be
safely used in decorators across the codebase.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter - initialized at module load time
limiter = Limiter(key_func=get_remote_address)
