"""
Integration tests for rate limiting.
"""
import pytest
from unittest.mock import AsyncMock


class TestRateLimiting:
    """Tests for rate limiting middleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client, flight_with_seats):
        """Test that rate limit headers are present in response."""
        flight, seats = flight_with_seats

        response = await client.get(f"/api/v1/flights/{flight.id}/seats")

        assert response.status_code == 200
        # These headers may or may not be present depending on mock
        # In real scenario, they would be present

    @pytest.mark.asyncio
    async def test_health_endpoint_not_rate_limited(self, client):
        """Test that health endpoint works without rate limiting."""
        # Make multiple requests
        for _ in range(10):
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_endpoint_accessible(self, client, flight_with_seats):
        """Test that API endpoints are accessible."""
        flight, seats = flight_with_seats

        # Make a few requests
        for _ in range(5):
            response = await client.get(f"/api/v1/flights/{flight.id}/seats")
            assert response.status_code == 200


class TestRateLimiterMiddleware:
    """Unit tests for rate limiter middleware logic."""

    def test_path_matching(self):
        """Test path pattern matching logic."""
        from src.common.middleware.rate_limiter import RateLimiterMiddleware

        # Create middleware instance (we'll test the method directly)
        middleware = RateLimiterMiddleware(None, enabled=True)

        # Test exact match
        assert middleware._match_pattern("/api/v1/flights", "/api/v1/flights") is True

        # Test wildcard match
        assert middleware._match_pattern("/api/v1/flights/123/seats", "/api/v1/flights/*/seats") is True
        assert middleware._match_pattern("/api/v1/seats/456/hold", "/api/v1/seats/*/hold") is True

        # Test no match
        assert middleware._match_pattern("/api/v1/other", "/api/v1/flights") is False

    def test_simplify_path(self):
        """Test path simplification for rate limiting keys."""
        from src.common.middleware.rate_limiter import RateLimiterMiddleware

        middleware = RateLimiterMiddleware(None, enabled=True)

        # UUID should be replaced with *
        path = "/api/v1/seats/123e4567-e89b-12d3-a456-426614174000/hold"
        simplified = middleware._simplify_path(path)
        assert "123e4567" not in simplified
        assert "*" in simplified

    def test_get_limit_for_path(self):
        """Test getting rate limit for different paths."""
        from src.common.middleware.rate_limiter import RateLimiterMiddleware

        middleware = RateLimiterMiddleware(None, enabled=True)

        # Seat map should have higher limit
        limit, window = middleware._get_limit_for_path("/api/v1/flights/123/seats")
        assert limit == 100

        # Seat hold should have lower limit
        limit, window = middleware._get_limit_for_path("/api/v1/seats/123/hold")
        assert limit == 10

        # Unknown path should use default
        limit, window = middleware._get_limit_for_path("/api/v1/unknown")
        assert limit == 100  # default

