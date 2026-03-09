"""
CheckIn service - business logic.
Orchestrates seat hold, baggage, and payment.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import logging

from src.domains.checkin.models import CheckIn, CheckInStatus
from src.domains.checkin.repository import CheckInRepository
from src.domains.checkin.schemas import CheckInResponse
from src.domains.seats.service import SeatService
from src.domains.seats.schemas import SeatResponse
from src.domains.seats.repository import SeatRepository
from src.domains.seats.models import SeatStatus
from src.domains.baggage.schemas import BaggageResponse
from src.domains.flights.repository import FlightRepository
from src.domains.passengers.repository import PassengerRepository
from src.common.exceptions import (
    CheckInNotFoundError, CheckInAlreadyExistsError,
    InvalidCheckInStateError, PaymentRequiredError,
    SeatHoldExpiredError, FlightNotFoundError, PassengerNotFoundError
)
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CheckInService:
    """Service for check-in business logic."""

    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self.repository = CheckInRepository(session)
        self.seat_service = SeatService(session, redis_client)
        self.seat_repository = SeatRepository(session)
        self.flight_repository = FlightRepository(session)
        self.passenger_repository = PassengerRepository(session)
        self.redis = redis_client

    async def start_checkin(
        self,
        passenger_id: UUID,
        flight_id: UUID,
        seat_id: UUID
    ) -> CheckInResponse:
        """
        Start the check-in process.
        1. Validate passenger and flight exist
        2. Check for existing check-in
        3. Hold the seat
        4. Create check-in record
        """
        # Validate passenger exists
        passenger = await self.passenger_repository.get_by_id(passenger_id)
        if not passenger:
            raise PassengerNotFoundError(str(passenger_id))

        # Validate flight exists
        flight = await self.flight_repository.get_by_id(flight_id)
        if not flight:
            raise FlightNotFoundError(str(flight_id))

        # Check for existing check-in
        existing = await self.repository.get_by_passenger_and_flight(passenger_id, flight_id)
        if existing:
            raise CheckInAlreadyExistsError(str(passenger_id), str(flight_id))

        # Hold the seat
        hold_response = await self.seat_service.hold_seat(seat_id, passenger_id)

        # Create check-in record
        checkin = CheckIn(
            passenger_id=passenger_id,
            flight_id=flight_id,
            seat_id=seat_id,
            status=CheckInStatus.IN_PROGRESS.value,
            started_at=datetime.utcnow()
        )
        checkin = await self.repository.create(checkin)

        # Schedule seat hold expiration
        try:
            from src.domains.seats.tasks import schedule_seat_hold_expiration
            schedule_seat_hold_expiration(str(seat_id), settings.seat_hold_duration_seconds)
        except Exception as e:
            logger.warning(f"Failed to schedule seat hold expiration: {e}")

        return await self._build_checkin_response(checkin)

    async def get_checkin(self, checkin_id: UUID) -> CheckInResponse:
        """Get check-in details."""
        checkin = await self.repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInNotFoundError(str(checkin_id))
        return await self._build_checkin_response(checkin)

    async def complete_checkin(self, checkin_id: UUID) -> CheckInResponse:
        """
        Complete the check-in process.
        1. Verify check-in is in progress (not waiting for payment)
        2. Verify seat is still held
        3. Confirm the seat
        4. Update check-in status
        """
        checkin = await self.repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInNotFoundError(str(checkin_id))

        # Check if waiting for payment
        if checkin.status == CheckInStatus.WAITING_FOR_PAYMENT.value:
            # Calculate pending payment
            pending = await self._calculate_pending_payment(checkin)
            raise PaymentRequiredError(str(checkin_id), pending)

        # Check if already completed
        if checkin.status == CheckInStatus.COMPLETED.value:
            raise InvalidCheckInStateError(str(checkin_id), checkin.status)

        # Get seat and check if still held
        seat = await self.seat_repository.get_by_id(checkin.seat_id)
        if not seat:
            raise SeatHoldExpiredError(str(checkin.seat_id))

        if seat.status == SeatStatus.AVAILABLE.value:
            # Hold expired
            raise SeatHoldExpiredError(str(checkin.seat_id))

        if seat.status == SeatStatus.CONFIRMED.value:
            # Already confirmed, just update check-in status
            pass
        else:
            # Check if hold expired
            if seat.hold_expires_at and seat.hold_expires_at < datetime.utcnow():
                raise SeatHoldExpiredError(str(checkin.seat_id))

            # Confirm the seat
            await self.seat_service.confirm_seat(checkin.seat_id, checkin.passenger_id)

        # Update check-in status
        checkin.status = CheckInStatus.COMPLETED.value
        checkin.completed_at = datetime.utcnow()
        await self.session.flush()

        return await self._build_checkin_response(checkin)

    async def set_waiting_for_payment(self, checkin_id: UUID) -> CheckInResponse:
        """Set check-in status to WAITING_FOR_PAYMENT."""
        checkin = await self.repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInNotFoundError(str(checkin_id))

        checkin.status = CheckInStatus.WAITING_FOR_PAYMENT.value
        await self.session.flush()

        return await self._build_checkin_response(checkin)

    async def resume_checkin(self, checkin_id: UUID) -> CheckInResponse:
        """Resume check-in after payment (set back to IN_PROGRESS)."""
        checkin = await self.repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInNotFoundError(str(checkin_id))

        if checkin.status != CheckInStatus.WAITING_FOR_PAYMENT.value:
            raise InvalidCheckInStateError(str(checkin_id), checkin.status, CheckInStatus.WAITING_FOR_PAYMENT.value)

        checkin.status = CheckInStatus.IN_PROGRESS.value
        await self.session.flush()

        return await self._build_checkin_response(checkin)

    async def _build_checkin_response(self, checkin: CheckIn) -> CheckInResponse:
        """Build a complete check-in response with all related data."""
        # Get seat info
        seat_response = None
        if checkin.seat_id:
            seat = await self.seat_repository.get_by_id(checkin.seat_id)
            if seat:
                seat_response = SeatResponse.model_validate(seat)

        # Calculate baggage totals
        total_weight = 0.0
        excess_fee = 0.0
        baggage_list = []

        for bag in checkin.baggage:
            total_weight += bag.weight_kg
            excess_fee += bag.excess_fee or 0
            baggage_list.append(BaggageResponse.model_validate(bag))

        return CheckInResponse(
            id=checkin.id,
            passenger_id=checkin.passenger_id,
            flight_id=checkin.flight_id,
            seat=seat_response,
            status=checkin.status,
            baggage=baggage_list,
            total_baggage_weight=total_weight,
            excess_fee=excess_fee,
            started_at=checkin.started_at,
            completed_at=checkin.completed_at
        )

    async def _calculate_pending_payment(self, checkin: CheckIn) -> float:
        """Calculate pending payment for excess baggage."""
        total_fee = 0.0
        for bag in checkin.baggage:
            if bag.excess_fee and not bag.fee_paid:
                total_fee += bag.excess_fee
        return total_fee

