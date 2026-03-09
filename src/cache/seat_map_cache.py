"""
Redis caching for seat maps.
"""
import json
import logging
from typing import Optional
from datetime import datetime
from uuid import UUID
import redis.asyncio as redis

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SeatMapCache:
    """
    Redis-based caching for seat maps.

    Uses cache-aside pattern:
    - Read: Check cache, if miss, read from DB and cache
    - Write: Invalidate cache, let next read repopulate
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = settings.cache_ttl_seconds

    def _get_cache_key(self, flight_id: UUID, seat_class: Optional[str] = None) -> str:
        """Generate cache key for seat map."""
        key = f"seat_map:{flight_id}"
        if seat_class:
            key += f":{seat_class}"
        return key

    async def get(self, flight_id: UUID, seat_class: Optional[str] = None) -> Optional[dict]:
        """
        Get cached seat map.

        Returns None if not cached or cache error.
        """
        try:
            key = self._get_cache_key(flight_id, seat_class)
            cached = await self.redis.get(key)

            if cached:
                data = json.loads(cached)
                data['cached'] = True
                logger.debug(f"Cache hit for {key}")
                return data

            logger.debug(f"Cache miss for {key}")
            return None

        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None

    async def set(
        self,
        flight_id: UUID,
        seat_map_data: dict,
        seat_class: Optional[str] = None
    ) -> bool:
        """
        Cache seat map data.

        Returns True if successful, False otherwise.
        """
        try:
            key = self._get_cache_key(flight_id, seat_class)

            # Add cache metadata
            data = seat_map_data.copy()
            data['cache_timestamp'] = datetime.utcnow().isoformat()
            data['cached'] = True

            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(data, default=str)
            )

            logger.debug(f"Cached seat map for {key}")
            return True

        except Exception as e:
            logger.warning(f"Cache write error: {e}")
            return False

    async def invalidate(self, flight_id: UUID) -> int:
        """
        Invalidate all cached seat maps for a flight.

        Returns the number of keys deleted.
        """
        try:
            pattern = f"seat_map:{flight_id}*"
            keys = []

            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                count = await self.redis.delete(*keys)
                logger.debug(f"Invalidated {count} cache keys for flight {flight_id}")
                return count

            return 0

        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            return 0

    async def invalidate_all(self) -> int:
        """
        Invalidate all seat map caches.

        Use with caution - only for testing or emergency.
        """
        try:
            pattern = "seat_map:*"
            keys = []

            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                count = await self.redis.delete(*keys)
                logger.info(f"Invalidated all {count} seat map cache keys")
                return count

            return 0

        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            return 0

