"""
Flight repository - database operations.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import date

from src.domains.flights.models import Flight


class FlightRepository:
    """Repository for flight database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, flight_id: UUID) -> Optional[Flight]:
        """Get a flight by ID."""
        stmt = select(Flight).where(Flight.id == flight_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
        departure_date: Optional[date] = None,
        departure_airport: Optional[str] = None
    ) -> tuple[List[Flight], int]:
        """Get all flights with optional filters."""
        # Base query
        stmt = select(Flight)
        count_stmt = select(func.count(Flight.id))

        # Apply filters
        if departure_date:
            stmt = stmt.where(func.date(Flight.departure_time) == departure_date)
            count_stmt = count_stmt.where(func.date(Flight.departure_time) == departure_date)

        if departure_airport:
            stmt = stmt.where(Flight.departure_airport == departure_airport.upper())
            count_stmt = count_stmt.where(Flight.departure_airport == departure_airport.upper())

        # Get total count
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar()

        # Apply pagination and ordering
        stmt = stmt.order_by(Flight.departure_time).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        flights = list(result.scalars().all())

        return flights, total

    async def create(self, flight: Flight) -> Flight:
        """Create a new flight."""
        self.session.add(flight)
        await self.session.flush()
        await self.session.refresh(flight)
        return flight

    async def get_by_flight_number(self, flight_number: str) -> Optional[Flight]:
        """Get flight by flight number."""
        stmt = select(Flight).where(Flight.flight_number == flight_number)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

