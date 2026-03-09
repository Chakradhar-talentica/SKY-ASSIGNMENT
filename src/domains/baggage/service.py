"""
Baggage service - business logic.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
import logging

from src.domains.baggage.models import Baggage
from src.domains.baggage.schemas import BaggageResponse, BaggageListResponse
from src.domains.checkin.repository import CheckInRepository
from src.domains.checkin.models import CheckInStatus
from src.common.exceptions import CheckInNotFoundError, InvalidCheckInStateError
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaggageService:
    """Service for baggage business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.checkin_repository = CheckInRepository(session)

    async def add_baggage(
        self,
        checkin_id: UUID,
        weight_kg: float
    ) -> BaggageListResponse:
        """
        Add baggage to a check-in.

        If total weight exceeds 25kg, calculates excess fee and
        sets check-in status to WAITING_FOR_PAYMENT.
        """
        # Get check-in
        checkin = await self.checkin_repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInNotFoundError(str(checkin_id))

        # Check if check-in is completed
        if checkin.status == CheckInStatus.COMPLETED.value:
            raise InvalidCheckInStateError(str(checkin_id), checkin.status)

        # Calculate current total weight
        current_weight = sum(bag.weight_kg for bag in checkin.baggage)
        new_total = current_weight + weight_kg

        # Calculate excess fee if over limit
        excess_fee = 0.0
        if new_total > settings.max_baggage_weight_kg:
            # Fee only applies to the portion over the limit
            excess_weight = max(0, new_total - settings.max_baggage_weight_kg)
            # If we had previous excess, calculate incremental
            previous_excess = max(0, current_weight - settings.max_baggage_weight_kg)
            new_excess = excess_weight - previous_excess
            excess_fee = new_excess * settings.excess_baggage_fee_per_kg

        # Create baggage record
        baggage = Baggage(
            checkin_id=checkin_id,
            weight_kg=weight_kg,
            excess_fee=excess_fee,
            fee_paid=False
        )
        self.session.add(baggage)
        await self.session.flush()

        # Update check-in status if payment required
        if excess_fee > 0:
            checkin.status = CheckInStatus.WAITING_FOR_PAYMENT.value
            await self.session.flush()
            logger.info(f"Check-in {checkin_id} requires payment of ${excess_fee}")

        return await self.get_baggage(checkin_id)

    async def get_baggage(self, checkin_id: UUID) -> BaggageListResponse:
        """Get all baggage for a check-in."""
        checkin = await self.checkin_repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInNotFoundError(str(checkin_id))

        # Refresh to get latest baggage items
        await self.session.refresh(checkin, attribute_names=['baggage'])

        baggage_list = []
        total_weight = 0.0
        total_excess_fee = 0.0
        unpaid_fee = 0.0

        for bag in checkin.baggage:
            baggage_list.append(BaggageResponse.model_validate(bag))
            total_weight += bag.weight_kg
            total_excess_fee += bag.excess_fee or 0
            if not bag.fee_paid:
                unpaid_fee += bag.excess_fee or 0

        return BaggageListResponse(
            baggage=baggage_list,
            total_weight=total_weight,
            total_excess_fee=total_excess_fee,
            max_allowed_weight=settings.max_baggage_weight_kg,
            requires_payment=unpaid_fee > 0
        )

    async def mark_fees_paid(self, checkin_id: UUID) -> None:
        """Mark all baggage fees as paid for a check-in."""
        checkin = await self.checkin_repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInNotFoundError(str(checkin_id))

        for bag in checkin.baggage:
            if not bag.fee_paid and bag.excess_fee > 0:
                bag.fee_paid = True

        await self.session.flush()

    def calculate_excess_fee(self, total_weight: float) -> float:
        """Calculate excess baggage fee."""
        if total_weight <= settings.max_baggage_weight_kg:
            return 0.0

        excess = total_weight - settings.max_baggage_weight_kg
        return excess * settings.excess_baggage_fee_per_kg

