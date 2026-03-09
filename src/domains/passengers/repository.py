"""
Passenger repository - database operations.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from src.domains.passengers.models import Passenger


class PassengerRepository:
    """Repository for passenger database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, passenger_id: UUID) -> Optional[Passenger]:
        """Get a passenger by ID."""
        stmt = select(Passenger).where(Passenger.id == passenger_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Passenger]:
        """Get a passenger by email."""
        stmt = select(Passenger).where(Passenger.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_booking_reference(self, booking_reference: str) -> Optional[Passenger]:
        """Get a passenger by booking reference."""
        stmt = select(Passenger).where(Passenger.booking_reference == booking_reference)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, passenger: Passenger) -> Passenger:
        """Create a new passenger."""
        self.session.add(passenger)
        await self.session.flush()
        await self.session.refresh(passenger)
        return passenger

