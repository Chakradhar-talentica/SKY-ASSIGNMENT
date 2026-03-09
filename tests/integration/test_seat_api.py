"""
Integration tests for Seat API endpoints.
"""
import pytest
from uuid import uuid4


class TestSeatMapAPI:
    """Tests for seat map API endpoints."""

    @pytest.mark.asyncio
    async def test_get_seat_map(self, client, flight_with_seats):
        """Test getting seat map for a flight."""
        flight, seats = flight_with_seats

        response = await client.get(f"/api/v1/flights/{flight.id}/seats")

        assert response.status_code == 200
        data = response.json()
        assert data["flight_id"] == str(flight.id)
        assert len(data["seats"]) == len(seats)
        assert data["summary"]["total"] == len(seats)
        assert data["summary"]["available"] == len(seats)

    @pytest.mark.asyncio
    async def test_get_seat_map_nonexistent_flight(self, client):
        """Test getting seat map for non-existent flight returns 404."""
        fake_id = uuid4()

        response = await client.get(f"/api/v1/flights/{fake_id}/seats")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FLIGHT_NOT_FOUND"


class TestSeatHoldAPI:
    """Tests for seat hold API endpoints."""

    @pytest.mark.asyncio
    async def test_hold_seat_success(self, client, sample_seat, sample_passenger):
        """Test holding a seat successfully."""
        response = await client.post(
            f"/api/v1/seats/{sample_seat.id}/hold",
            json={"passenger_id": str(sample_passenger.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["seat"]["status"] == "HELD"
        assert data["seat"]["held_by"] == str(sample_passenger.id)
        assert data["seconds_remaining"] > 0

    @pytest.mark.asyncio
    async def test_hold_seat_already_held(self, client, held_seat):
        """Test holding an already held seat returns 409."""
        other_passenger = uuid4()

        response = await client.post(
            f"/api/v1/seats/{held_seat.id}/hold",
            json={"passenger_id": str(other_passenger)}
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SEAT_NOT_AVAILABLE"

    @pytest.mark.asyncio
    async def test_hold_confirmed_seat(self, client, confirmed_seat):
        """Test holding a confirmed seat returns 409."""
        passenger_id = uuid4()

        response = await client.post(
            f"/api/v1/seats/{confirmed_seat.id}/hold",
            json={"passenger_id": str(passenger_id)}
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_hold_nonexistent_seat(self, client):
        """Test holding a non-existent seat returns 404."""
        fake_seat_id = uuid4()
        passenger_id = uuid4()

        response = await client.post(
            f"/api/v1/seats/{fake_seat_id}/hold",
            json={"passenger_id": str(passenger_id)}
        )

        assert response.status_code == 404


class TestSeatReleaseAPI:
    """Tests for seat release API endpoints."""

    @pytest.mark.asyncio
    async def test_release_seat_success(self, client, held_seat, sample_passenger):
        """Test releasing a held seat successfully."""
        response = await client.post(
            f"/api/v1/seats/{held_seat.id}/release",
            json={"passenger_id": str(sample_passenger.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "AVAILABLE"
        assert data["held_by"] is None

    @pytest.mark.asyncio
    async def test_release_seat_wrong_passenger(self, client, held_seat):
        """Test releasing seat by wrong passenger returns error."""
        other_passenger = uuid4()

        response = await client.post(
            f"/api/v1/seats/{held_seat.id}/release",
            json={"passenger_id": str(other_passenger)}
        )

        assert response.status_code == 409


class TestSeatConfirmAPI:
    """Tests for seat confirm API endpoints."""

    @pytest.mark.asyncio
    async def test_confirm_seat_success(self, client, held_seat, sample_passenger):
        """Test confirming a held seat successfully."""
        response = await client.post(
            f"/api/v1/seats/{held_seat.id}/confirm",
            json={"passenger_id": str(sample_passenger.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CONFIRMED"
        assert data["confirmed_by"] == str(sample_passenger.id)

    @pytest.mark.asyncio
    async def test_confirm_seat_wrong_passenger(self, client, held_seat):
        """Test confirming seat by wrong passenger returns error."""
        other_passenger = uuid4()

        response = await client.post(
            f"/api/v1/seats/{held_seat.id}/confirm",
            json={"passenger_id": str(other_passenger)}
        )

        assert response.status_code == 403

