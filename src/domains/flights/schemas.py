"""
Flight Pydantic schemas.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class FlightBase(BaseModel):
    """Base flight schema."""
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    aircraft_type: Optional[str] = None


class FlightCreate(FlightBase):
    """Schema for creating a flight."""
    pass


class FlightResponse(FlightBase):
    """Schema for flight response."""
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlightListResponse(BaseModel):
    """Schema for list of flights."""
    flights: List[FlightResponse]
    total: int
    limit: int
    offset: int

