"""
Unit tests for the Seat service.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domains.seats.service import SeatService
from src.domains.seats.models import Seat, SeatStatus
from src.domains.flights.models import Flight
from src.domains.passengers.models import Passenger
from src.common.exceptions import (
    SeatNotFoundError, SeatNotAvailableError,
    SeatHoldExpiredError, UnauthorizedSeatOperationError
)


class TestSeatService:
    """Tests for SeatService."""

    @pytest.mark.asyncio
    async def test_hold_available_seat(
        self,
        db_session,
        sample_flight,
        sample_seat,
        sample_passenger
    ):
        """Test holding an available seat succeeds."""
        service = SeatService(db_session)

        result = await service.hold_seat(sample_seat.id, sample_passenger.id)

        assert result.seat.status == SeatStatus.HELD.value
        assert result.seat.held_by == sample_passenger.id
        assert result.seconds_remaining > 0
        assert result.seconds_remaining <= 120

    @pytest.mark.asyncio
    async def test_hold_already_held_seat_fails(
        self,
        db_session,
        held_seat
    ):
        """Test holding an already held seat fails."""
        service = SeatService(db_session)
        another_passenger_id = uuid4()

        with pytest.raises(SeatNotAvailableError):
            await service.hold_seat(held_seat.id, another_passenger_id)

    @pytest.mark.asyncio
    async def test_hold_confirmed_seat_fails(
        self,
        db_session,
        confirmed_seat
    ):
        """Test holding a confirmed seat fails."""
        service = SeatService(db_session)
        passenger_id = uuid4()

        with pytest.raises(SeatNotAvailableError):
            await service.hold_seat(confirmed_seat.id, passenger_id)

    @pytest.mark.asyncio
    async def test_hold_nonexistent_seat_fails(self, db_session):
        """Test holding a non-existent seat fails."""
        service = SeatService(db_session)
        fake_seat_id = uuid4()
        passenger_id = uuid4()

        with pytest.raises(SeatNotFoundError):
            await service.hold_seat(fake_seat_id, passenger_id)

    @pytest.mark.asyncio
    async def test_confirm_held_seat(
        self,
        db_session,
        held_seat,
        sample_passenger
    ):
        """Test confirming a held seat succeeds."""
        service = SeatService(db_session)

        result = await service.confirm_seat(held_seat.id, sample_passenger.id)

        assert result.status == SeatStatus.CONFIRMED.value
        assert result.confirmed_by == sample_passenger.id

    @pytest.mark.asyncio
    async def test_confirm_seat_by_different_passenger_fails(
        self,
        db_session,
        held_seat
    ):
        """Test confirming a seat held by another passenger fails."""
        service = SeatService(db_session)
        another_passenger_id = uuid4()

        with pytest.raises(UnauthorizedSeatOperationError):
            await service.confirm_seat(held_seat.id, another_passenger_id)

    @pytest.mark.asyncio
    async def test_confirm_available_seat_fails(
        self,
        db_session,
        sample_seat,
        sample_passenger
    ):
        """Test confirming an available seat fails."""
        service = SeatService(db_session)

        with pytest.raises(SeatNotAvailableError):
            await service.confirm_seat(sample_seat.id, sample_passenger.id)

    @pytest.mark.asyncio
    async def test_release_held_seat(
        self,
        db_session,
        held_seat,
        sample_passenger
    ):
        """Test releasing a held seat succeeds."""
        service = SeatService(db_session)

        result = await service.release_seat(held_seat.id, sample_passenger.id)

        assert result.status == SeatStatus.AVAILABLE.value
        assert result.held_by is None

    @pytest.mark.asyncio
    async def test_release_seat_by_different_passenger_fails(
        self,
        db_session,
        held_seat
    ):
        """Test releasing a seat held by another passenger fails."""
        service = SeatService(db_session)
        another_passenger_id = uuid4()

        with pytest.raises(SeatNotAvailableError):
            await service.release_seat(held_seat.id, another_passenger_id)

    @pytest.mark.asyncio
    async def test_get_seat_map(
        self,
        db_session,
        flight_with_seats
    ):
        """Test getting seat map for a flight."""
        flight, seats = flight_with_seats
        service = SeatService(db_session)

        result = await service.get_seat_map(flight.id)

        assert result.flight_id == flight.id
        assert len(result.seats) == len(seats)
        assert result.summary.total == len(seats)
        assert result.summary.available == len(seats)
        assert result.summary.held == 0
        assert result.summary.confirmed == 0

    @pytest.mark.asyncio
    async def test_confirmed_seat_cannot_change(
        self,
        db_session,
        confirmed_seat,
        sample_passenger
    ):
        """Test that confirmed seats cannot be modified."""
        service = SeatService(db_session)

        # Cannot hold
        with pytest.raises(SeatNotAvailableError):
            await service.hold_seat(confirmed_seat.id, sample_passenger.id)

        # Cannot release
        with pytest.raises(SeatNotAvailableError):
            await service.release_seat(confirmed_seat.id, sample_passenger.id)


class TestSeatExpiration:
    """Tests for seat hold expiration."""

    @pytest.mark.asyncio
    async def test_expire_held_seat(
        self,
        db_session,
        sample_flight,
        sample_passenger
    ):
        """Test expiring a held seat."""
        # Create a seat with expired hold
        expired_seat = Seat(
            id=uuid4(),
            flight_id=sample_flight.id,
            seat_number="99A",
            seat_class="economy",
            status=SeatStatus.HELD.value,
            held_by=sample_passenger.id,
            held_at=datetime.utcnow() - timedelta(minutes=5),
            hold_expires_at=datetime.utcnow() - timedelta(minutes=3),
            created_at=datetime.utcnow()
        )
        db_session.add(expired_seat)
        await db_session.flush()

        service = SeatService(db_session)
        result = await service.expire_seat_hold(expired_seat.id)

        assert result.status == SeatStatus.AVAILABLE.value
        assert result.held_by is None

    @pytest.mark.asyncio
    async def test_confirm_expired_seat_fails(
        self,
        db_session,
        sample_flight,
        sample_passenger
    ):
        """Test confirming an expired seat fails."""
        # Create a seat with expired hold
        expired_seat = Seat(
            id=uuid4(),
            flight_id=sample_flight.id,
            seat_number="99B",
            seat_class="economy",
            status=SeatStatus.HELD.value,
            held_by=sample_passenger.id,
            held_at=datetime.utcnow() - timedelta(minutes=5),
            hold_expires_at=datetime.utcnow() - timedelta(minutes=3),
            created_at=datetime.utcnow()
        )
        db_session.add(expired_seat)
        await db_session.flush()

        service = SeatService(db_session)

        with pytest.raises(SeatHoldExpiredError):
            await service.confirm_seat(expired_seat.id, sample_passenger.id)

