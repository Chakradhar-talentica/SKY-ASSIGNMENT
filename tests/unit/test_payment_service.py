"""
Unit tests for the Payment service.
"""
import pytest
from datetime import datetime
from uuid import uuid4

from src.domains.payments.service import PaymentService
from src.domains.payments.models import PaymentStatus
from src.domains.checkin.models import CheckInStatus
from src.domains.baggage.models import Baggage
from src.common.exceptions import (
    CheckInNotFoundError, InvalidCheckInStateError, PaymentFailedError
)


class TestPaymentService:
    """Tests for PaymentService."""

    @pytest.mark.asyncio
    async def test_process_payment_success(
        self,
        db_session,
        sample_checkin
    ):
        """Test processing payment successfully."""
        # Set up: add overweight baggage and set status
        baggage = Baggage(
            id=uuid4(),
            checkin_id=sample_checkin.id,
            weight_kg=30.0,
            excess_fee=50.0,  # 5kg * $10
            fee_paid=False,
            created_at=datetime.utcnow()
        )
        db_session.add(baggage)
        sample_checkin.status = CheckInStatus.WAITING_FOR_PAYMENT.value
        await db_session.flush()

        service = PaymentService(db_session)

        result = await service.process_payment(
            checkin_id=sample_checkin.id,
            amount=50.0,
            payment_method="card"
        )

        assert result.status == PaymentStatus.SUCCESS.value
        assert result.amount == 50.0
        assert result.paid_at is not None

        # Check check-in status is back to IN_PROGRESS
        await db_session.refresh(sample_checkin)
        assert sample_checkin.status == CheckInStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_process_payment_wrong_amount_fails(
        self,
        db_session,
        sample_checkin
    ):
        """Test payment with wrong amount fails."""
        # Set up: add overweight baggage
        baggage = Baggage(
            id=uuid4(),
            checkin_id=sample_checkin.id,
            weight_kg=30.0,
            excess_fee=50.0,
            fee_paid=False,
            created_at=datetime.utcnow()
        )
        db_session.add(baggage)
        sample_checkin.status = CheckInStatus.WAITING_FOR_PAYMENT.value
        await db_session.flush()

        service = PaymentService(db_session)

        with pytest.raises(PaymentFailedError):
            await service.process_payment(
                checkin_id=sample_checkin.id,
                amount=25.0,  # Wrong amount
                payment_method="card"
            )

    @pytest.mark.asyncio
    async def test_process_payment_wrong_status_fails(
        self,
        db_session,
        sample_checkin
    ):
        """Test payment when not waiting for payment fails."""
        # Check-in is IN_PROGRESS, not WAITING_FOR_PAYMENT
        service = PaymentService(db_session)

        with pytest.raises(InvalidCheckInStateError):
            await service.process_payment(
                checkin_id=sample_checkin.id,
                amount=50.0,
                payment_method="card"
            )

    @pytest.mark.asyncio
    async def test_process_payment_nonexistent_checkin_fails(self, db_session):
        """Test payment for non-existent check-in fails."""
        service = PaymentService(db_session)
        fake_id = uuid4()

        with pytest.raises(CheckInNotFoundError):
            await service.process_payment(
                checkin_id=fake_id,
                amount=50.0,
                payment_method="card"
            )

    @pytest.mark.asyncio
    async def test_payment_marks_baggage_fees_paid(
        self,
        db_session,
        sample_checkin
    ):
        """Test payment marks baggage fees as paid."""
        # Set up: add multiple baggage with fees
        baggage1 = Baggage(
            id=uuid4(),
            checkin_id=sample_checkin.id,
            weight_kg=20.0,
            excess_fee=0.0,
            fee_paid=False,
            created_at=datetime.utcnow()
        )
        baggage2 = Baggage(
            id=uuid4(),
            checkin_id=sample_checkin.id,
            weight_kg=15.0,
            excess_fee=100.0,  # Over limit
            fee_paid=False,
            created_at=datetime.utcnow()
        )
        db_session.add(baggage1)
        db_session.add(baggage2)
        sample_checkin.status = CheckInStatus.WAITING_FOR_PAYMENT.value
        await db_session.flush()

        service = PaymentService(db_session)

        await service.process_payment(
            checkin_id=sample_checkin.id,
            amount=100.0,
            payment_method="card"
        )

        # Refresh and check baggage
        await db_session.refresh(baggage2)
        assert baggage2.fee_paid is True

