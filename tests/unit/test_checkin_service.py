"""
Unit tests for the CheckIn service.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domains.checkin.service import CheckInService
from src.domains.checkin.models import CheckIn, CheckInStatus
from src.domains.seats.models import SeatStatus
from src.common.exceptions import (
    CheckInNotFoundError, CheckInAlreadyExistsError,
    InvalidCheckInStateError, PaymentRequiredError,
    SeatHoldExpiredError
)


class TestCheckInService:
    """Tests for CheckInService."""

    @pytest.mark.asyncio
    async def test_start_checkin_success(
        self,
        db_session,
        sample_flight,
        sample_passenger,
        sample_seat
    ):
        """Test starting check-in successfully."""
        service = CheckInService(db_session)

        result = await service.start_checkin(
            passenger_id=sample_passenger.id,
            flight_id=sample_flight.id,
            seat_id=sample_seat.id
        )

        assert result.status == CheckInStatus.IN_PROGRESS.value
        assert result.passenger_id == sample_passenger.id
        assert result.flight_id == sample_flight.id
        assert result.seat is not None
        assert result.seat.status == SeatStatus.HELD.value

    @pytest.mark.asyncio
    async def test_start_checkin_twice_fails(
        self,
        db_session,
        sample_checkin,
        sample_flight,
        sample_passenger,
        sample_seat
    ):
        """Test starting check-in twice for same passenger/flight fails."""
        service = CheckInService(db_session)

        # Create another available seat
        from src.domains.seats.models import Seat
        another_seat = Seat(
            id=uuid4(),
            flight_id=sample_flight.id,
            seat_number="99Z",
            seat_class="economy",
            status=SeatStatus.AVAILABLE.value,
            created_at=datetime.utcnow()
        )
        db_session.add(another_seat)
        await db_session.flush()

        with pytest.raises(CheckInAlreadyExistsError):
            await service.start_checkin(
                passenger_id=sample_passenger.id,
                flight_id=sample_flight.id,
                seat_id=another_seat.id
            )

    @pytest.mark.asyncio
    async def test_get_checkin(self, db_session, sample_checkin):
        """Test getting check-in details."""
        service = CheckInService(db_session)

        result = await service.get_checkin(sample_checkin.id)

        assert result.id == sample_checkin.id
        assert result.status == sample_checkin.status

    @pytest.mark.asyncio
    async def test_get_nonexistent_checkin_fails(self, db_session):
        """Test getting non-existent check-in fails."""
        service = CheckInService(db_session)
        fake_id = uuid4()

        with pytest.raises(CheckInNotFoundError):
            await service.get_checkin(fake_id)

    @pytest.mark.asyncio
    async def test_complete_checkin_success(
        self,
        db_session,
        sample_checkin,
        held_seat
    ):
        """Test completing check-in successfully."""
        service = CheckInService(db_session)

        result = await service.complete_checkin(sample_checkin.id)

        assert result.status == CheckInStatus.COMPLETED.value
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_checkin_waiting_payment_fails(
        self,
        db_session,
        sample_checkin
    ):
        """Test completing check-in waiting for payment fails."""
        # Set checkin to waiting for payment
        sample_checkin.status = CheckInStatus.WAITING_FOR_PAYMENT.value
        await db_session.flush()

        service = CheckInService(db_session)

        with pytest.raises(PaymentRequiredError):
            await service.complete_checkin(sample_checkin.id)

    @pytest.mark.asyncio
    async def test_complete_already_completed_checkin_fails(
        self,
        db_session,
        sample_checkin
    ):
        """Test completing an already completed check-in fails."""
        # Set checkin to completed
        sample_checkin.status = CheckInStatus.COMPLETED.value
        sample_checkin.completed_at = datetime.utcnow()
        await db_session.flush()

        service = CheckInService(db_session)

        with pytest.raises(InvalidCheckInStateError):
            await service.complete_checkin(sample_checkin.id)


class TestCheckInStatusTransitions:
    """Tests for check-in status transitions."""

    @pytest.mark.asyncio
    async def test_set_waiting_for_payment(
        self,
        db_session,
        sample_checkin
    ):
        """Test setting check-in to waiting for payment."""
        service = CheckInService(db_session)

        result = await service.set_waiting_for_payment(sample_checkin.id)

        assert result.status == CheckInStatus.WAITING_FOR_PAYMENT.value

    @pytest.mark.asyncio
    async def test_resume_checkin(
        self,
        db_session,
        sample_checkin
    ):
        """Test resuming check-in after payment."""
        # Set to waiting for payment
        sample_checkin.status = CheckInStatus.WAITING_FOR_PAYMENT.value
        await db_session.flush()

        service = CheckInService(db_session)

        result = await service.resume_checkin(sample_checkin.id)

        assert result.status == CheckInStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_resume_checkin_wrong_status_fails(
        self,
        db_session,
        sample_checkin
    ):
        """Test resuming check-in from wrong status fails."""
        # Check-in is IN_PROGRESS, not WAITING_FOR_PAYMENT
        service = CheckInService(db_session)

        with pytest.raises(InvalidCheckInStateError):
            await service.resume_checkin(sample_checkin.id)

