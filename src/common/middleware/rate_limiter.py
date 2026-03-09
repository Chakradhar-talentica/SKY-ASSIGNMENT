"""
Redis-based rate limiting middleware.
Uses sliding window counter algorithm.
"""
import time
import logging
from typing import Optional, Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis sliding window.

    Rate limits are configured per endpoint pattern.
    """

    # Default rate limits per endpoint pattern
    DEFAULT_LIMITS: Dict[str, tuple] = {
        "/api/v1/flights/*/seats": (100, 60),  # 100 requests per 60 seconds
        "/api/v1/seats/*/hold": (10, 60),       # 10 requests per 60 seconds
        "/api/v1/seats/*/confirm": (10, 60),
        "/api/v1/seats/*/release": (10, 60),
        "/api/v1/checkin": (20, 60),
        "default": (100, 60),
    }

    def __init__(self, app, redis_client: Optional[redis.Redis] = None, enabled: bool = True):
        super().__init__(app)
        self.redis_client = redis_client
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process each request through rate limiting."""
        if not self.enabled:
            return await call_next(request)

        # Get Redis client from app state if not provided
        redis_client = self.redis_client
        if redis_client is None and hasattr(request.app.state, 'redis'):
            redis_client = request.app.state.redis

        if redis_client is None:
            # If Redis is not available, allow the request (graceful degradation)
            logger.warning("Redis not available for rate limiting, allowing request")
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)

        # Get rate limit for this endpoint
        limit, window = self._get_limit_for_path(request.url.path)

        # Check rate limit
        try:
            is_allowed, current_count = await self._check_rate_limit(
                redis_client, client_ip, request.url.path, limit, window
            )
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request on error (graceful degradation)
            return await call_next(request)

        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {limit} requests per {window} seconds.",
                        "details": {
                            "limit": limit,
                            "window_seconds": window,
                            "retry_after": window
                        }
                    }
                },
                headers={"Retry-After": str(window)}
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current_count))
        response.headers["X-RateLimit-Window"] = str(window)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _get_limit_for_path(self, path: str) -> tuple:
        """Get rate limit configuration for a path."""
        # Check for matching patterns
        for pattern, limit in self.DEFAULT_LIMITS.items():
            if pattern == "default":
                continue
            if self._match_pattern(path, pattern):
                return limit

        return self.DEFAULT_LIMITS["default"]

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching with * wildcard."""
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")

        if len(pattern_parts) > len(path_parts):
            return False

        for i, part in enumerate(pattern_parts):
            if part == "*":
                continue
            if i >= len(path_parts) or part != path_parts[i]:
                return False

        return True

    async def _check_rate_limit(
        self,
        redis_client: redis.Redis,
        client_ip: str,
        path: str,
        limit: int,
        window: int
    ) -> tuple:
        """
        Check if request is within rate limit.
        Uses sliding window counter algorithm.

        Returns: (is_allowed, current_count)
        """
        # Create a key based on IP and simplified path
        simplified_path = self._simplify_path(path)
        key = f"rate_limit:{client_ip}:{simplified_path}"

        current_time = int(time.time())
        window_start = current_time - window

        # Use pipeline for atomic operations
        pipe = redis_client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Add current request timestamp
        pipe.zadd(key, {str(current_time): current_time})

        # Count requests in window
        pipe.zcard(key)

        # Set expiry on the key
        pipe.expire(key, window)

        results = await pipe.execute()
        current_count = results[2]

        return current_count <= limit, current_count

    def _simplify_path(self, path: str) -> str:
        """Simplify path for rate limiting key (remove UUIDs)."""
        import re
        # Replace UUIDs with placeholder
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        return re.sub(uuid_pattern, '*', path, flags=re.IGNORECASE)

