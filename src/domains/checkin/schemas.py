"""
CheckIn Pydantic schemas.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from src.domains.seats.schemas import SeatResponse
from src.domains.baggage.schemas import BaggageResponse


class StartCheckInRequest(BaseModel):
    """Schema for starting check-in."""
    passenger_id: UUID
    flight_id: UUID
    seat_id: UUID


class CheckInResponse(BaseModel):
    """Schema for check-in response."""
    id: UUID
    passenger_id: UUID
    flight_id: UUID
    seat: Optional[SeatResponse] = None
    status: str
    baggage: List[BaggageResponse] = []
    total_baggage_weight: float = 0.0
    excess_fee: float = 0.0
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CheckInStatusResponse(BaseModel):
    """Schema for check-in status."""
    id: UUID
    status: str
    seat_number: Optional[str] = None
    can_complete: bool = False
    pending_payment: float = 0.0

