"""
Unit tests for Flight service.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domains.flights.service import FlightService
from src.domains.flights.models import Flight
from src.common.exceptions import FlightNotFoundError


class TestFlightService:
    """Tests for FlightService."""

    @pytest.mark.asyncio
    async def test_get_flight_success(self, db_session, sample_flight):
        """Test getting a flight successfully."""
        service = FlightService(db_session)

        result = await service.get_flight(sample_flight.id)

        assert result.id == sample_flight.id
        assert result.flight_number == sample_flight.flight_number

    @pytest.mark.asyncio
    async def test_get_flight_not_found(self, db_session):
        """Test getting a non-existent flight fails."""
        service = FlightService(db_session)
        fake_id = uuid4()

        with pytest.raises(FlightNotFoundError):
            await service.get_flight(fake_id)

    @pytest.mark.asyncio
    async def test_get_flights(self, db_session, sample_flight):
        """Test getting flights list."""
        service = FlightService(db_session)

        flights, total = await service.get_flights()

        assert total >= 1
        assert len(flights) >= 1

    @pytest.mark.asyncio
    async def test_get_flights_with_pagination(self, db_session, sample_flight):
        """Test getting flights with pagination."""
        service = FlightService(db_session)

        flights, total = await service.get_flights(limit=5, offset=0)

        assert len(flights) <= 5

    @pytest.mark.asyncio
    async def test_create_flight(self, db_session):
        """Test creating a flight."""
        service = FlightService(db_session)
        flight_data = {
            "flight_number": "TEST01",
            "departure_airport": "ABC",
            "arrival_airport": "XYZ",
            "departure_time": datetime.utcnow() + timedelta(hours=10),
            "arrival_time": datetime.utcnow() + timedelta(hours=15),
            "aircraft_type": "Test Aircraft"
        }

        result = await service.create_flight(flight_data)

        assert result.flight_number == "TEST01"
        assert result.departure_airport == "ABC"

