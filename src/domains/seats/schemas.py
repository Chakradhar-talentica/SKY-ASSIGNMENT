"""
Seat Pydantic schemas.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from src.domains.seats.models import SeatStatus, SeatClass


class SeatBase(BaseModel):
    """Base seat schema."""
    seat_number: str
    seat_class: str = SeatClass.ECONOMY.value


class SeatResponse(BaseModel):
    """Schema for seat response."""
    id: UUID
    seat_number: str
    seat_class: str
    status: str
    held_by: Optional[UUID] = None
    hold_expires_at: Optional[datetime] = None
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SeatMapSummary(BaseModel):
    """Summary of seat availability."""
    total: int
    available: int
    held: int
    confirmed: int


class SeatMapResponse(BaseModel):
    """Schema for seat map response."""
    flight_id: UUID
    flight_number: str
    seats: List[SeatResponse]
    summary: SeatMapSummary
    cached: bool = False
    cache_timestamp: Optional[datetime] = None


class HoldSeatRequest(BaseModel):
    """Schema for hold seat request."""
    passenger_id: UUID


class HoldSeatResponse(BaseModel):
    """Schema for hold seat response."""
    seat: SeatResponse
    hold_expires_at: datetime
    seconds_remaining: int


class ReleaseSeatRequest(BaseModel):
    """Schema for release seat request."""
    passenger_id: UUID


class ConfirmSeatRequest(BaseModel):
    """Schema for confirm seat request."""
    passenger_id: UUID


class SeatStateHistoryResponse(BaseModel):
    """Schema for seat state history."""
    id: UUID
    seat_id: UUID
    previous_status: Optional[str]
    new_status: str
    changed_by: Optional[UUID]
    change_reason: Optional[str]
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)

