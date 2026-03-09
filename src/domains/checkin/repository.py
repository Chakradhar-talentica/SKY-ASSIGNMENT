"""
CheckIn repository - database operations.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID

from src.domains.checkin.models import CheckIn, CheckInStatus


class CheckInRepository:
    """Repository for check-in database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, checkin_id: UUID) -> Optional[CheckIn]:
        """Get a check-in by ID."""
        stmt = select(CheckIn).where(CheckIn.id == checkin_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_passenger_and_flight(
        self,
        passenger_id: UUID,
        flight_id: UUID
    ) -> Optional[CheckIn]:
        """Get a check-in by passenger and flight."""
        stmt = select(CheckIn).where(
            and_(
                CheckIn.passenger_id == passenger_id,
                CheckIn.flight_id == flight_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, checkin: CheckIn) -> CheckIn:
        """Create a new check-in."""
        self.session.add(checkin)
        await self.session.flush()
        await self.session.refresh(checkin)
        return checkin

    async def update_status(self, checkin_id: UUID, status: CheckInStatus) -> Optional[CheckIn]:
        """Update check-in status."""
        checkin = await self.get_by_id(checkin_id)
        if checkin:
            checkin.status = status.value
            await self.session.flush()
            await self.session.refresh(checkin)
        return checkin

