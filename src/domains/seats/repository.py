"""
Seat repository - database operations with concurrency control.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from sqlalchemy.exc import OperationalError
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging

from src.domains.seats.models import Seat, SeatStatus, SeatStateHistory
from src.common.exceptions import SeatNotFoundError, SeatNotAvailableError, SeatLockError

logger = logging.getLogger(__name__)


class SeatRepository:
    """Repository for seat database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, seat_id: UUID) -> Optional[Seat]:
        """Get a seat by ID."""
        stmt = select(Seat).where(Seat.id == seat_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, seat_id: UUID, nowait: bool = True) -> Optional[Seat]:
        """
        Get a seat by ID with row-level lock for update.
        Uses FOR UPDATE NOWAIT to fail fast on lock contention.
        """
        stmt = select(Seat).where(Seat.id == seat_id)

        if nowait:
            stmt = stmt.with_for_update(nowait=True)
        else:
            stmt = stmt.with_for_update()

        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except OperationalError as e:
            # Lock could not be acquired
            if "could not obtain lock" in str(e).lower() or "lock not available" in str(e).lower():
                logger.warning(f"Could not acquire lock for seat {seat_id}")
                raise SeatLockError(str(seat_id))
            raise

    async def get_seats_by_flight(
        self,
        flight_id: UUID,
        seat_class: Optional[str] = None
    ) -> List[Seat]:
        """Get all seats for a flight."""
        stmt = select(Seat).where(Seat.flight_id == flight_id)

        if seat_class:
            stmt = stmt.where(Seat.seat_class == seat_class)

        stmt = stmt.order_by(Seat.seat_number)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def hold_seat(
        self,
        seat_id: UUID,
        passenger_id: UUID,
        hold_duration_seconds: int = 120
    ) -> Seat:
        """
        Attempt to hold a seat with proper locking.
        Uses SELECT FOR UPDATE NOWAIT for conflict-free assignment.
        """
        # Get seat with lock
        seat = await self.get_by_id_for_update(seat_id)

        if not seat:
            raise SeatNotFoundError(str(seat_id))

        if seat.status != SeatStatus.AVAILABLE.value:
            raise SeatNotAvailableError(str(seat_id), seat.status, seat.seat_number)

        # Update seat to HELD
        now = datetime.utcnow()
        seat.status = SeatStatus.HELD.value
        seat.held_by = passenger_id
        seat.held_at = now
        seat.hold_expires_at = now + timedelta(seconds=hold_duration_seconds)
        seat.updated_at = now

        # Record state change
        await self._record_state_change(
            seat_id=seat_id,
            previous_status=SeatStatus.AVAILABLE.value,
            new_status=SeatStatus.HELD.value,
            changed_by=passenger_id,
            change_reason="passenger_selected_seat"
        )

        await self.session.flush()
        return seat

    async def confirm_seat(self, seat_id: UUID, passenger_id: UUID) -> Seat:
        """
        Confirm a held seat.
        Only the passenger who holds the seat can confirm it.
        """
        seat = await self.get_by_id_for_update(seat_id)

        if not seat:
            raise SeatNotFoundError(str(seat_id))

        if seat.status != SeatStatus.HELD.value:
            raise SeatNotAvailableError(str(seat_id), seat.status, seat.seat_number)

        if seat.held_by != passenger_id:
            raise SeatNotAvailableError(str(seat_id), seat.status, seat.seat_number)

        # Update to CONFIRMED
        now = datetime.utcnow()
        previous_status = seat.status
        seat.status = SeatStatus.CONFIRMED.value
        seat.confirmed_by = passenger_id
        seat.confirmed_at = now
        seat.held_by = None
        seat.held_at = None
        seat.hold_expires_at = None
        seat.updated_at = now

        # Record state change
        await self._record_state_change(
            seat_id=seat_id,
            previous_status=previous_status,
            new_status=SeatStatus.CONFIRMED.value,
            changed_by=passenger_id,
            change_reason="passenger_confirmed_seat"
        )

        await self.session.flush()
        return seat

    async def release_seat(self, seat_id: UUID, passenger_id: UUID) -> Seat:
        """
        Release a held seat back to AVAILABLE.
        Only the passenger who holds the seat can release it.
        """
        seat = await self.get_by_id_for_update(seat_id)

        if not seat:
            raise SeatNotFoundError(str(seat_id))

        if seat.status != SeatStatus.HELD.value:
            raise SeatNotAvailableError(str(seat_id), seat.status, seat.seat_number)

        if seat.held_by != passenger_id:
            raise SeatNotAvailableError(str(seat_id), seat.status, seat.seat_number)

        # Update to AVAILABLE
        now = datetime.utcnow()
        previous_status = seat.status
        seat.status = SeatStatus.AVAILABLE.value
        seat.held_by = None
        seat.held_at = None
        seat.hold_expires_at = None
        seat.updated_at = now

        # Record state change
        await self._record_state_change(
            seat_id=seat_id,
            previous_status=previous_status,
            new_status=SeatStatus.AVAILABLE.value,
            changed_by=passenger_id,
            change_reason="passenger_released_seat"
        )

        await self.session.flush()
        return seat

    async def expire_hold(self, seat_id: UUID) -> Optional[Seat]:
        """
        Expire a seat hold, returning it to AVAILABLE.
        Used by background tasks.
        """
        seat = await self.get_by_id_for_update(seat_id, nowait=False)

        if not seat:
            return None

        # Only expire if still HELD
        if seat.status != SeatStatus.HELD.value:
            return seat

        # Check if hold has actually expired
        now = datetime.utcnow()
        if seat.hold_expires_at and seat.hold_expires_at > now:
            # Not yet expired
            return seat

        # Update to AVAILABLE
        previous_status = seat.status
        seat.status = SeatStatus.AVAILABLE.value
        seat.held_by = None
        seat.held_at = None
        seat.hold_expires_at = None
        seat.updated_at = now

        # Record state change
        await self._record_state_change(
            seat_id=seat_id,
            previous_status=previous_status,
            new_status=SeatStatus.AVAILABLE.value,
            changed_by=None,
            change_reason="hold_expired_automatically"
        )

        await self.session.flush()
        return seat

    async def cleanup_expired_holds(self) -> int:
        """
        Cleanup all expired seat holds.
        Returns the number of seats released.
        """
        now = datetime.utcnow()

        # Find expired holds
        stmt = select(Seat).where(
            and_(
                Seat.status == SeatStatus.HELD.value,
                Seat.hold_expires_at < now
            )
        ).with_for_update(skip_locked=True)  # Skip locked to avoid contention

        result = await self.session.execute(stmt)
        expired_seats = list(result.scalars().all())

        count = 0
        for seat in expired_seats:
            previous_status = seat.status
            seat.status = SeatStatus.AVAILABLE.value
            seat.held_by = None
            seat.held_at = None
            seat.hold_expires_at = None
            seat.updated_at = now

            # Record state change
            await self._record_state_change(
                seat_id=seat.id,
                previous_status=previous_status,
                new_status=SeatStatus.AVAILABLE.value,
                changed_by=None,
                change_reason="hold_expired_cleanup"
            )
            count += 1

        if count > 0:
            await self.session.flush()
            logger.info(f"Cleaned up {count} expired seat holds")

        return count

    async def get_seat_counts_by_flight(self, flight_id: UUID) -> dict:
        """Get seat counts by status for a flight."""
        stmt = select(
            Seat.status,
            func.count(Seat.id)
        ).where(Seat.flight_id == flight_id).group_by(Seat.status)

        result = await self.session.execute(stmt)
        counts = {status: 0 for status in [SeatStatus.AVAILABLE.value, SeatStatus.HELD.value, SeatStatus.CONFIRMED.value]}

        for status, count in result:
            counts[status] = count

        return counts

    async def create(self, seat: Seat) -> Seat:
        """Create a new seat."""
        self.session.add(seat)
        await self.session.flush()
        await self.session.refresh(seat)
        return seat

    async def _record_state_change(
        self,
        seat_id: UUID,
        previous_status: Optional[str],
        new_status: str,
        changed_by: Optional[UUID],
        change_reason: str
    ) -> SeatStateHistory:
        """Record a seat state change in history."""
        history = SeatStateHistory(
            seat_id=seat_id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=changed_by,
            change_reason=change_reason,
            changed_at=datetime.utcnow()
        )
        self.session.add(history)
        return history

