"""
Seat service - business logic.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime
import logging

from src.domains.seats.models import Seat, SeatStatus
from src.domains.seats.repository import SeatRepository
from src.domains.seats.schemas import (
    SeatResponse, SeatMapResponse, SeatMapSummary,
    HoldSeatResponse
)
from src.domains.flights.repository import FlightRepository
from src.common.exceptions import (
    SeatNotFoundError, FlightNotFoundError, SeatHoldExpiredError,
    UnauthorizedSeatOperationError
)
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SeatService:
    """Service for seat business logic."""

    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self.repository = SeatRepository(session)
        self.flight_repository = FlightRepository(session)
        self.redis = redis_client

    async def get_seat_map(
        self,
        flight_id: UUID,
        seat_class: Optional[str] = None,
        use_cache: bool = True
    ) -> SeatMapResponse:
        """
        Get the seat map for a flight.
        Uses Redis caching for performance.
        """
        # Try cache first
        cache_key = f"seat_map:{flight_id}"
        if seat_class:
            cache_key += f":{seat_class}"

        if use_cache and self.redis:
            try:
                cached = await self._get_cached_seat_map(cache_key)
                if cached:
                    return cached
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        # Get from database
        flight = await self.flight_repository.get_by_id(flight_id)
        if not flight:
            raise FlightNotFoundError(str(flight_id))

        seats = await self.repository.get_seats_by_flight(flight_id, seat_class)
        counts = await self.repository.get_seat_counts_by_flight(flight_id)

        seat_responses = [SeatResponse.model_validate(s) for s in seats]

        response = SeatMapResponse(
            flight_id=flight_id,
            flight_number=flight.flight_number,
            seats=seat_responses,
            summary=SeatMapSummary(
                total=len(seats),
                available=counts.get(SeatStatus.AVAILABLE.value, 0),
                held=counts.get(SeatStatus.HELD.value, 0),
                confirmed=counts.get(SeatStatus.CONFIRMED.value, 0)
            ),
            cached=False,
            cache_timestamp=None
        )

        # Cache the result
        if use_cache and self.redis:
            try:
                await self._cache_seat_map(cache_key, response)
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

        return response

    async def hold_seat(
        self,
        seat_id: UUID,
        passenger_id: UUID
    ) -> HoldSeatResponse:
        """
        Hold a seat for a passenger.
        """
        seat = await self.repository.hold_seat(
            seat_id=seat_id,
            passenger_id=passenger_id,
            hold_duration_seconds=settings.seat_hold_duration_seconds
        )

        # Invalidate cache
        await self._invalidate_seat_cache(seat.flight_id)

        # Calculate seconds remaining
        now = datetime.utcnow()
        seconds_remaining = int((seat.hold_expires_at - now).total_seconds())

        return HoldSeatResponse(
            seat=SeatResponse.model_validate(seat),
            hold_expires_at=seat.hold_expires_at,
            seconds_remaining=seconds_remaining
        )

    async def confirm_seat(
        self,
        seat_id: UUID,
        passenger_id: UUID
    ) -> SeatResponse:
        """
        Confirm a held seat.
        """
        # Get seat first to check state
        seat = await self.repository.get_by_id(seat_id)
        if not seat:
            raise SeatNotFoundError(str(seat_id))

        # Check if hold has expired
        if seat.status == SeatStatus.HELD.value:
            if seat.held_by != passenger_id:
                raise UnauthorizedSeatOperationError(str(seat_id), str(passenger_id))

            now = datetime.utcnow()
            if seat.hold_expires_at and seat.hold_expires_at < now:
                # Expire the hold
                await self.repository.expire_hold(seat_id)
                raise SeatHoldExpiredError(str(seat_id))

        seat = await self.repository.confirm_seat(seat_id, passenger_id)

        # Invalidate cache
        await self._invalidate_seat_cache(seat.flight_id)

        return SeatResponse.model_validate(seat)

    async def release_seat(
        self,
        seat_id: UUID,
        passenger_id: UUID
    ) -> SeatResponse:
        """
        Release a held seat.
        """
        seat = await self.repository.release_seat(seat_id, passenger_id)

        # Invalidate cache
        await self._invalidate_seat_cache(seat.flight_id)

        return SeatResponse.model_validate(seat)

    async def expire_seat_hold(self, seat_id: UUID) -> Optional[SeatResponse]:
        """
        Expire a seat hold (called by background task).
        """
        seat = await self.repository.expire_hold(seat_id)

        if seat:
            await self._invalidate_seat_cache(seat.flight_id)
            return SeatResponse.model_validate(seat)

        return None

    async def cleanup_expired_holds(self) -> int:
        """
        Cleanup all expired seat holds.
        """
        count = await self.repository.cleanup_expired_holds()

        # Note: This is a batch operation, cache invalidation should be
        # handled more carefully in production (e.g., track affected flights)

        return count

    async def get_seat(self, seat_id: UUID) -> SeatResponse:
        """Get a single seat by ID."""
        seat = await self.repository.get_by_id(seat_id)
        if not seat:
            raise SeatNotFoundError(str(seat_id))
        return SeatResponse.model_validate(seat)

    async def _get_cached_seat_map(self, cache_key: str) -> Optional[SeatMapResponse]:
        """Get seat map from cache."""
        if not self.redis:
            return None

        import json
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            data['cached'] = True
            return SeatMapResponse(**data)
        return None

    async def _cache_seat_map(self, cache_key: str, response: SeatMapResponse) -> None:
        """Cache seat map."""
        if not self.redis:
            return

        import json
        data = response.model_dump(mode='json')
        data['cache_timestamp'] = datetime.utcnow().isoformat()
        await self.redis.setex(
            cache_key,
            settings.cache_ttl_seconds,
            json.dumps(data, default=str)
        )

    async def _invalidate_seat_cache(self, flight_id: UUID) -> None:
        """Invalidate seat map cache for a flight."""
        if not self.redis:
            return

        try:
            # Delete all cache keys related to this flight
            pattern = f"seat_map:{flight_id}*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.redis.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} cache keys for flight {flight_id}")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

