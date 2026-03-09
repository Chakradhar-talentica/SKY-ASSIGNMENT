"""
Passenger Pydantic schemas.
"""
from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
from typing import Optional
from uuid import UUID


class PassengerBase(BaseModel):
    """Base passenger schema."""
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    booking_reference: str


class PassengerCreate(PassengerBase):
    """Schema for creating a passenger."""
    pass


class PassengerResponse(PassengerBase):
    """Schema for passenger response."""
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

