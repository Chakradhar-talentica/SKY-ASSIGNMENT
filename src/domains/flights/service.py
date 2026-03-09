"""
Flight service - business logic.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import date

from src.domains.flights.models import Flight
from src.domains.flights.repository import FlightRepository
from src.common.exceptions import FlightNotFoundError


class FlightService:
    """Service for flight business logic."""

    def __init__(self, session: AsyncSession):
        self.repository = FlightRepository(session)

    async def get_flight(self, flight_id: UUID) -> Flight:
        """Get a flight by ID."""
        flight = await self.repository.get_by_id(flight_id)
        if not flight:
            raise FlightNotFoundError(str(flight_id))
        return flight

    async def get_flights(
        self,
        limit: int = 20,
        offset: int = 0,
        departure_date: Optional[date] = None,
        departure_airport: Optional[str] = None
    ) -> tuple[List[Flight], int]:
        """Get all flights with optional filters."""
        return await self.repository.get_all(
            limit=limit,
            offset=offset,
            departure_date=departure_date,
            departure_airport=departure_airport
        )

    async def create_flight(self, flight_data: dict) -> Flight:
        """Create a new flight."""
        flight = Flight(**flight_data)
        return await self.repository.create(flight)

