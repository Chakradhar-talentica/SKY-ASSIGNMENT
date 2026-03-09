"""
Payment Pydantic schemas.
"""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class PaymentRequest(BaseModel):
    """Schema for payment request."""
    amount: float = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(default="card", description="Payment method (card, cash, wallet)")


class PaymentResponse(BaseModel):
    """Schema for payment response."""
    id: UUID
    amount: float
    status: str
    payment_method: str
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

