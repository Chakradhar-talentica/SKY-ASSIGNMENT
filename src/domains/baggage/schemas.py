"""
Baggage Pydantic schemas.
"""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List
from uuid import UUID


class AddBaggageRequest(BaseModel):
    """Schema for adding baggage."""
    weight_kg: float = Field(..., gt=0, le=50, description="Weight in kg (max 50)")


class BaggageResponse(BaseModel):
    """Schema for baggage response."""
    id: UUID
    weight_kg: float
    excess_fee: float = 0.0
    fee_paid: bool = False

    model_config = ConfigDict(from_attributes=True)


class BaggageListResponse(BaseModel):
    """Schema for baggage list."""
    baggage: List[BaggageResponse]
    total_weight: float
    total_excess_fee: float
    max_allowed_weight: float = 25.0
    requires_payment: bool = False

