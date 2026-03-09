"""
Payment API router.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.config.database import get_db_session
from src.domains.payments.service import PaymentService
from src.domains.payments.schemas import PaymentRequest, PaymentResponse

router = APIRouter(tags=["Payments"])


@router.post("/checkin/{checkin_id}/pay", response_model=PaymentResponse)
async def process_payment(
    checkin_id: UUID,
    request_body: PaymentRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Process payment for excess baggage fees.

    The check-in must be in WAITING_FOR_PAYMENT status.
    The payment amount must match the total excess baggage fee.

    After successful payment:
    - All baggage fees are marked as paid
    - Check-in status returns to IN_PROGRESS
    - Passenger can complete check-in

    Note: This is a simulated payment service for demonstration.
    """
    service = PaymentService(session)
    return await service.process_payment(
        checkin_id=checkin_id,
        amount=request_body.amount,
        payment_method=request_body.payment_method
    )

