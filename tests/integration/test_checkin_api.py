"""
Integration tests for Check-in API endpoints.
"""
import pytest
from uuid import uuid4


class TestCheckInAPI:
    """Tests for check-in API endpoints."""

    @pytest.mark.asyncio
    async def test_start_checkin_success(
        self,
        client,
        sample_flight,
        sample_passenger,
        sample_seat
    ):
        """Test starting check-in successfully."""
        response = await client.post(
            "/api/v1/checkin/start",
            json={
                "passenger_id": str(sample_passenger.id),
                "flight_id": str(sample_flight.id),
                "seat_id": str(sample_seat.id)
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["passenger_id"] == str(sample_passenger.id)
        assert data["seat"] is not None
        assert data["seat"]["status"] == "HELD"

    @pytest.mark.asyncio
    async def test_start_checkin_invalid_passenger(
        self,
        client,
        sample_flight,
        sample_seat
    ):
        """Test starting check-in with invalid passenger returns 404."""
        fake_passenger = uuid4()

        response = await client.post(
            "/api/v1/checkin/start",
            json={
                "passenger_id": str(fake_passenger),
                "flight_id": str(sample_flight.id),
                "seat_id": str(sample_seat.id)
            }
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PASSENGER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_start_checkin_invalid_flight(
        self,
        client,
        sample_passenger,
        sample_seat
    ):
        """Test starting check-in with invalid flight returns 404."""
        fake_flight = uuid4()

        response = await client.post(
            "/api/v1/checkin/start",
            json={
                "passenger_id": str(sample_passenger.id),
                "flight_id": str(fake_flight),
                "seat_id": str(sample_seat.id)
            }
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FLIGHT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_checkin(self, client, sample_checkin):
        """Test getting check-in details."""
        response = await client.get(f"/api/v1/checkin/{sample_checkin.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_checkin.id)
        assert data["status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_get_checkin_not_found(self, client):
        """Test getting non-existent check-in returns 404."""
        fake_id = uuid4()

        response = await client.get(f"/api/v1/checkin/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_complete_checkin_success(
        self,
        client,
        sample_checkin,
        held_seat
    ):
        """Test completing check-in successfully."""
        response = await client.post(f"/api/v1/checkin/{sample_checkin.id}/complete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["completed_at"] is not None


class TestBaggageAPI:
    """Tests for baggage API endpoints."""

    @pytest.mark.asyncio
    async def test_add_baggage_under_limit(self, client, sample_checkin):
        """Test adding baggage under weight limit."""
        response = await client.post(
            f"/api/v1/checkin/{sample_checkin.id}/baggage",
            json={"weight_kg": 20.0}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["total_weight"] == 20.0
        assert data["requires_payment"] is False

    @pytest.mark.asyncio
    async def test_add_baggage_over_limit(self, client, sample_checkin):
        """Test adding baggage over weight limit triggers payment requirement."""
        response = await client.post(
            f"/api/v1/checkin/{sample_checkin.id}/baggage",
            json={"weight_kg": 30.0}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["total_weight"] == 30.0
        assert data["total_excess_fee"] == 50.0  # 5kg * $10
        assert data["requires_payment"] is True

    @pytest.mark.asyncio
    async def test_get_baggage(self, client, checkin_with_baggage):
        """Test getting baggage for a check-in."""
        checkin, baggage = checkin_with_baggage

        response = await client.get(f"/api/v1/checkin/{checkin.id}/baggage")

        assert response.status_code == 200
        data = response.json()
        assert len(data["baggage"]) == 1
        assert data["total_weight"] == 20.0


class TestPaymentAPI:
    """Tests for payment API endpoints."""

    @pytest.mark.asyncio
    async def test_process_payment_success(self, client, sample_checkin, db_session):
        """Test processing payment successfully."""
        from src.domains.baggage.models import Baggage
        from src.domains.checkin.models import CheckInStatus
        from datetime import datetime

        # Add overweight baggage
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
        await db_session.commit()

        response = await client.post(
            f"/api/v1/checkin/{sample_checkin.id}/pay",
            json={"amount": 50.0, "payment_method": "card"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["amount"] == 50.0

    @pytest.mark.asyncio
    async def test_process_payment_wrong_status(self, client, sample_checkin):
        """Test payment when not waiting for payment returns error."""
        response = await client.post(
            f"/api/v1/checkin/{sample_checkin.id}/pay",
            json={"amount": 50.0, "payment_method": "card"}
        )

        assert response.status_code == 400


class TestFullCheckInFlow:
    """End-to-end tests for complete check-in flow."""

    @pytest.mark.asyncio
    async def test_complete_checkin_flow_no_excess_baggage(
        self,
        client,
        sample_flight,
        sample_passenger,
        sample_seat
    ):
        """Test complete check-in flow without excess baggage."""
        # 1. Start check-in
        response = await client.post(
            "/api/v1/checkin/start",
            json={
                "passenger_id": str(sample_passenger.id),
                "flight_id": str(sample_flight.id),
                "seat_id": str(sample_seat.id)
            }
        )
        assert response.status_code == 201
        checkin_id = response.json()["id"]

        # 2. Add baggage (under limit)
        response = await client.post(
            f"/api/v1/checkin/{checkin_id}/baggage",
            json={"weight_kg": 20.0}
        )
        assert response.status_code == 201
        assert response.json()["requires_payment"] is False

        # 3. Complete check-in
        response = await client.post(f"/api/v1/checkin/{checkin_id}/complete")
        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_complete_checkin_flow_with_excess_baggage(
        self,
        client,
        sample_flight,
        sample_passenger,
        sample_seat
    ):
        """Test complete check-in flow with excess baggage and payment."""
        # 1. Start check-in
        response = await client.post(
            "/api/v1/checkin/start",
            json={
                "passenger_id": str(sample_passenger.id),
                "flight_id": str(sample_flight.id),
                "seat_id": str(sample_seat.id)
            }
        )
        assert response.status_code == 201
        checkin_id = response.json()["id"]

        # 2. Add overweight baggage
        response = await client.post(
            f"/api/v1/checkin/{checkin_id}/baggage",
            json={"weight_kg": 30.0}
        )
        assert response.status_code == 201
        assert response.json()["requires_payment"] is True
        excess_fee = response.json()["total_excess_fee"]

        # 3. Try to complete - should fail
        response = await client.post(f"/api/v1/checkin/{checkin_id}/complete")
        assert response.status_code == 402  # Payment required

        # 4. Process payment
        response = await client.post(
            f"/api/v1/checkin/{checkin_id}/pay",
            json={"amount": excess_fee, "payment_method": "card"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "SUCCESS"

        # 5. Complete check-in
        response = await client.post(f"/api/v1/checkin/{checkin_id}/complete")
        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED"

