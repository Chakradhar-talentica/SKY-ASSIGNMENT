"""
Unit tests for the Baggage service.
"""
import pytest
from datetime import datetime
from uuid import uuid4

from src.domains.baggage.service import BaggageService
from src.domains.baggage.models import Baggage
from src.domains.checkin.models import CheckInStatus
from src.common.exceptions import CheckInNotFoundError, InvalidCheckInStateError
from src.config.settings import get_settings

settings = get_settings()


class TestBaggageService:
    """Tests for BaggageService."""

    @pytest.mark.asyncio
    async def test_add_baggage_under_limit(
        self,
        db_session,
        sample_checkin
    ):
        """Test adding baggage under weight limit."""
        service = BaggageService(db_session)

        result = await service.add_baggage(sample_checkin.id, 20.0)

        assert result.total_weight == 20.0
        assert result.total_excess_fee == 0.0
        assert result.requires_payment is False

    @pytest.mark.asyncio
    async def test_add_baggage_over_limit(
        self,
        db_session,
        sample_checkin
    ):
        """Test adding baggage over weight limit triggers payment."""
        service = BaggageService(db_session)

        # Add 30kg baggage (5kg over 25kg limit)
        result = await service.add_baggage(sample_checkin.id, 30.0)

        assert result.total_weight == 30.0
        expected_fee = 5.0 * settings.excess_baggage_fee_per_kg  # 5kg * $10 = $50
        assert result.total_excess_fee == expected_fee
        assert result.requires_payment is True

        # Check that check-in status changed
        await db_session.refresh(sample_checkin)
        assert sample_checkin.status == CheckInStatus.WAITING_FOR_PAYMENT.value

    @pytest.mark.asyncio
    async def test_add_multiple_baggage(
        self,
        db_session,
        sample_checkin
    ):
        """Test adding multiple pieces of baggage."""
        service = BaggageService(db_session)

        # Add first bag (20kg, under limit)
        result = await service.add_baggage(sample_checkin.id, 20.0)
        assert result.total_weight == 20.0
        assert result.requires_payment is False

        # Add second bag (10kg, total now 30kg - 5kg over limit)
        result = await service.add_baggage(sample_checkin.id, 10.0)
        assert result.total_weight == 30.0
        expected_fee = 5.0 * settings.excess_baggage_fee_per_kg
        assert result.total_excess_fee == expected_fee
        assert result.requires_payment is True

    @pytest.mark.asyncio
    async def test_get_baggage(
        self,
        db_session,
        checkin_with_baggage
    ):
        """Test getting baggage for a check-in."""
        checkin, baggage = checkin_with_baggage
        service = BaggageService(db_session)

        result = await service.get_baggage(checkin.id)

        assert len(result.baggage) == 1
        assert result.total_weight == 20.0
        assert result.max_allowed_weight == settings.max_baggage_weight_kg

    @pytest.mark.asyncio
    async def test_add_baggage_to_completed_checkin_fails(
        self,
        db_session,
        sample_checkin
    ):
        """Test adding baggage to completed check-in fails."""
        sample_checkin.status = CheckInStatus.COMPLETED.value
        await db_session.flush()

        service = BaggageService(db_session)

        with pytest.raises(InvalidCheckInStateError):
            await service.add_baggage(sample_checkin.id, 10.0)

    @pytest.mark.asyncio
    async def test_add_baggage_nonexistent_checkin_fails(self, db_session):
        """Test adding baggage to non-existent check-in fails."""
        service = BaggageService(db_session)
        fake_id = uuid4()

        with pytest.raises(CheckInNotFoundError):
            await service.add_baggage(fake_id, 10.0)

    @pytest.mark.asyncio
    async def test_mark_fees_paid(
        self,
        db_session,
        sample_checkin
    ):
        """Test marking baggage fees as paid."""
        service = BaggageService(db_session)

        # Add overweight baggage
        await service.add_baggage(sample_checkin.id, 30.0)

        # Mark fees paid
        await service.mark_fees_paid(sample_checkin.id)

        # Check baggage is marked as paid
        result = await service.get_baggage(sample_checkin.id)
        for bag in result.baggage:
            if bag.excess_fee > 0:
                assert bag.fee_paid is True

    @pytest.mark.asyncio
    async def test_calculate_excess_fee(self, db_session):
        """Test excess fee calculation."""
        service = BaggageService(db_session)

        # Under limit - no fee
        assert service.calculate_excess_fee(20.0) == 0.0

        # At limit - no fee
        assert service.calculate_excess_fee(25.0) == 0.0

        # Over limit
        expected = 5.0 * settings.excess_baggage_fee_per_kg
        assert service.calculate_excess_fee(30.0) == expected

