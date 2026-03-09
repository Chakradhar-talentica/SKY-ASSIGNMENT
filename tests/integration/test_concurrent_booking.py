"""
Integration tests for concurrent seat booking.
Tests the conflict-free seat assignment requirement.

Note: True concurrent locking tests require PostgreSQL.
SQLite doesn't support FOR UPDATE NOWAIT, so concurrent tests
will behave differently. Use PostgreSQL for production testing.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from src.domains.seats.models import Seat, SeatStatus
from src.domains.passengers.models import Passenger


class TestConcurrentSeatBooking:
    """Tests for concurrent seat booking scenarios."""

    @pytest.mark.asyncio
    async def test_sequential_seat_hold_second_fails(
        self,
        client,
        sample_seat,
        db_session
    ):
        """
        Test that second hold request fails when seat is already held.
        This is a sequential test that verifies the basic locking behavior.
        """
        # Create two passengers
        passenger1 = Passenger(
            id=uuid4(),
            first_name="First",
            last_name="User",
            email=f"first.{uuid4().hex[:6]}@example.com",
            phone="+1234567890",
            booking_reference="FIRST01",
            created_at=datetime.utcnow()
        )
        passenger2 = Passenger(
            id=uuid4(),
            first_name="Second",
            last_name="User",
            email=f"second.{uuid4().hex[:6]}@example.com",
            phone="+0987654321",
            booking_reference="SECOND01",
            created_at=datetime.utcnow()
        )
        db_session.add(passenger1)
        db_session.add(passenger2)
        await db_session.commit()

        # First passenger holds the seat
        response1 = await client.post(
            f"/api/v1/seats/{sample_seat.id}/hold",
            json={"passenger_id": str(passenger1.id)}
        )
        assert response1.status_code == 200
        assert response1.json()["seat"]["status"] == "HELD"

        # Second passenger tries to hold the same seat - should fail
        response2 = await client.post(
            f"/api/v1/seats/{sample_seat.id}/hold",
            json={"passenger_id": str(passenger2.id)}
        )
        assert response2.status_code == 409

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Concurrent locking requires PostgreSQL, not SQLite")
    async def test_concurrent_seat_hold_only_one_succeeds(
        self,
        client,
        sample_seat,
        db_session
    ):
        """
        Test that only one of multiple concurrent hold requests succeeds.

        NOTE: This test requires PostgreSQL to work correctly.
        SQLite doesn't support FOR UPDATE NOWAIT locking.
        """
        # Create multiple passengers
        passengers = []
        for i in range(5):
            passenger = Passenger(
                id=uuid4(),
                first_name=f"Test{i}",
                last_name="User",
                email=f"test{i}.{uuid4().hex[:6]}@example.com",
                phone=f"+123456789{i}",
                booking_reference=f"REF{i:03d}",
                created_at=datetime.utcnow()
            )
            db_session.add(passenger)
            passengers.append(passenger)
        await db_session.commit()

        # Make concurrent hold requests
        async def try_hold(passenger_id):
            response = await client.post(
                f"/api/v1/seats/{sample_seat.id}/hold",
                json={"passenger_id": str(passenger_id)}
            )
            return response

        # Execute all requests concurrently
        results = await asyncio.gather(
            *[try_hold(p.id) for p in passengers],
            return_exceptions=True
        )

        # Count successes and failures
        successes = [r for r in results if hasattr(r, 'status_code') and r.status_code == 200]
        failures = [r for r in results if hasattr(r, 'status_code') and r.status_code == 409]

        # Exactly one should succeed
        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"

        # The rest should fail with conflict
        assert len(failures) == len(passengers) - 1

        # Verify the seat is held
        success_data = successes[0].json()
        assert success_data["seat"]["status"] == "HELD"

    @pytest.mark.asyncio
    async def test_different_seats_can_be_held_concurrently(
        self,
        client,
        flight_with_seats,
        db_session
    ):
        """Test that different seats can be held by different passengers concurrently."""
        flight, seats = flight_with_seats

        # Create passengers
        passengers = []
        for i in range(3):
            passenger = Passenger(
                id=uuid4(),
                first_name=f"Concurrent{i}",
                last_name="User",
                email=f"concurrent{i}.{uuid4().hex[:6]}@example.com",
                phone=f"+987654321{i}",
                booking_reference=f"CON{i:03d}",
                created_at=datetime.utcnow()
            )
            db_session.add(passenger)
            passengers.append(passenger)
        await db_session.commit()

        # Each passenger tries to hold a different seat
        async def try_hold(seat_id, passenger_id):
            response = await client.post(
                f"/api/v1/seats/{seat_id}/hold",
                json={"passenger_id": str(passenger_id)}
            )
            return response

        # Execute all requests concurrently
        results = await asyncio.gather(
            *[try_hold(seats[i].id, passengers[i].id) for i in range(3)],
            return_exceptions=True
        )

        # All should succeed
        successes = [r for r in results if hasattr(r, 'status_code') and r.status_code == 200]
        assert len(successes) == 3, f"Expected 3 successes, got {len(successes)}"

    @pytest.mark.asyncio
    async def test_no_duplicate_seat_assignment(
        self,
        client,
        sample_seat,
        db_session
    ):
        """Verify no duplicate seat assignments can occur."""
        # Create two passengers
        passenger1 = Passenger(
            id=uuid4(),
            first_name="First",
            last_name="User",
            email=f"first.{uuid4().hex[:6]}@example.com",
            booking_reference="FIR001",
            created_at=datetime.utcnow()
        )
        passenger2 = Passenger(
            id=uuid4(),
            first_name="Second",
            last_name="User",
            email=f"second.{uuid4().hex[:6]}@example.com",
            booking_reference="SEC001",
            created_at=datetime.utcnow()
        )
        db_session.add(passenger1)
        db_session.add(passenger2)
        await db_session.commit()

        # First passenger holds the seat
        response1 = await client.post(
            f"/api/v1/seats/{sample_seat.id}/hold",
            json={"passenger_id": str(passenger1.id)}
        )
        assert response1.status_code == 200

        # Second passenger tries to hold the same seat
        response2 = await client.post(
            f"/api/v1/seats/{sample_seat.id}/hold",
            json={"passenger_id": str(passenger2.id)}
        )
        assert response2.status_code == 409

        # First passenger confirms
        response3 = await client.post(
            f"/api/v1/seats/{sample_seat.id}/confirm",
            json={"passenger_id": str(passenger1.id)}
        )
        assert response3.status_code == 200

        # Verify seat is confirmed by first passenger only
        response4 = await client.get(f"/api/v1/seats/{sample_seat.id}")
        assert response4.status_code == 200
        data = response4.json()
        assert data["status"] == "CONFIRMED"
        assert data["confirmed_by"] == str(passenger1.id)


class TestSeatLifecycleIntegrity:
    """Tests for seat lifecycle state integrity."""

    @pytest.mark.asyncio
    async def test_confirmed_seat_cannot_be_held(
        self,
        client,
        confirmed_seat
    ):
        """Test that a confirmed seat cannot be held."""
        passenger_id = uuid4()

        response = await client.post(
            f"/api/v1/seats/{confirmed_seat.id}/hold",
            json={"passenger_id": str(passenger_id)}
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SEAT_NOT_AVAILABLE"

    @pytest.mark.asyncio
    async def test_confirmed_seat_cannot_be_released(
        self,
        client,
        confirmed_seat,
        sample_passenger
    ):
        """Test that a confirmed seat cannot be released."""
        response = await client.post(
            f"/api/v1/seats/{confirmed_seat.id}/release",
            json={"passenger_id": str(sample_passenger.id)}
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_available_seat_cannot_be_confirmed(
        self,
        client,
        sample_seat,
        sample_passenger
    ):
        """Test that an available seat cannot be directly confirmed."""
        response = await client.post(
            f"/api/v1/seats/{sample_seat.id}/confirm",
            json={"passenger_id": str(sample_passenger.id)}
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_available_seat_cannot_be_released(
        self,
        client,
        sample_seat,
        sample_passenger
    ):
        """Test that an available seat cannot be released."""
        response = await client.post(
            f"/api/v1/seats/{sample_seat.id}/release",
            json={"passenger_id": str(sample_passenger.id)}
        )

        assert response.status_code == 409

