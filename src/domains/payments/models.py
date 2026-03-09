"""
Payment SQLAlchemy model.
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from src.config.database import Base


class PaymentStatus(str, enum.Enum):
    """Payment status enum."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Payment(Base):
    """Payment database model."""

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checkin_id = Column(UUID(as_uuid=True), ForeignKey("checkins.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default=PaymentStatus.PENDING.value)
    payment_method = Column(String(50), default="card")
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    checkin = relationship("CheckIn", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id} (${self.amount} - {self.status})>"

