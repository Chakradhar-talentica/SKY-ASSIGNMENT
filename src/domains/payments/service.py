"""
Payment service - business logic (simulated).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import logging

from src.domains.payments.models import Payment, PaymentStatus
from src.domains.payments.schemas import PaymentResponse
from src.domains.checkin.repository import CheckInRepository
from src.domains.checkin.models import CheckInStatus
from src.domains.baggage.service import BaggageService
from src.common.exceptions import (
    CheckInNotFoundError, InvalidCheckInStateError, PaymentFailedError
)

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service for payment business logic.

    Note: This is a simulated payment service. In production, this would
    integrate with a real payment gateway.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.checkin_repository = CheckInRepository(session)
        self.baggage_service = BaggageService(session)

    async def process_payment(
        self,
        checkin_id: UUID,
        amount: float,
        payment_method: str = "card"
    ) -> PaymentResponse:
        """
        Process a payment for excess baggage.

        This is a simulated payment - it always succeeds unless
        the amount doesn't match the required fee.
        """
        # Get check-in
        checkin = await self.checkin_repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInNotFoundError(str(checkin_id))

        # Verify check-in is waiting for payment
        if checkin.status != CheckInStatus.WAITING_FOR_PAYMENT.value:
            raise InvalidCheckInStateError(
                str(checkin_id),
                checkin.status,
                CheckInStatus.WAITING_FOR_PAYMENT.value
            )

        # Calculate required payment
        required_amount = 0.0
        for bag in checkin.baggage:
            if not bag.fee_paid and bag.excess_fee > 0:
                required_amount += bag.excess_fee

        if required_amount <= 0:
            raise InvalidCheckInStateError(str(checkin_id), checkin.status)

        # Validate amount (allow slight variance for rounding)
        if abs(amount - required_amount) > 0.01:
            raise PaymentFailedError(
                f"Payment amount ${amount:.2f} does not match required fee ${required_amount:.2f}"
            )

        # Create payment record
        payment = Payment(
            checkin_id=checkin_id,
            amount=amount,
            status=PaymentStatus.PENDING.value,
            payment_method=payment_method
        )
        self.session.add(payment)
        await self.session.flush()

        # Simulate payment processing (always succeeds in demo)
        try:
            await self._simulate_payment_gateway(payment)

            # Payment successful
            payment.status = PaymentStatus.SUCCESS.value
            payment.paid_at = datetime.utcnow()

            # Mark baggage fees as paid
            await self.baggage_service.mark_fees_paid(checkin_id)

            # Resume check-in
            checkin.status = CheckInStatus.IN_PROGRESS.value
            await self.session.flush()

            logger.info(f"Payment of ${amount} processed successfully for check-in {checkin_id}")

        except Exception as e:
            payment.status = PaymentStatus.FAILED.value
            await self.session.flush()
            logger.error(f"Payment failed for check-in {checkin_id}: {e}")
            raise PaymentFailedError(str(e))

        return PaymentResponse.model_validate(payment)

    async def _simulate_payment_gateway(self, payment: Payment) -> bool:
        """
        Simulate payment gateway processing.

        In production, this would:
        1. Call external payment API
        2. Handle various response codes
        3. Implement retry logic
        4. Handle webhooks
        """
        # Simulate network delay
        import asyncio
        await asyncio.sleep(0.1)

        # Always succeed in simulation
        # In real implementation, this might fail based on:
        # - Invalid card
        # - Insufficient funds
        # - Network errors
        # - Fraud detection
        return True

