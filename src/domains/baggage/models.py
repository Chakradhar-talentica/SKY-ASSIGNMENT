"""
Baggage SQLAlchemy model.
"""
from sqlalchemy import Column, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.config.database import Base


class Baggage(Base):
    """Baggage database model."""

    __tablename__ = "baggage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checkin_id = Column(UUID(as_uuid=True), ForeignKey("checkins.id"), nullable=False)
    weight_kg = Column(Float, nullable=False)
    excess_fee = Column(Float, default=0.0)
    fee_paid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    checkin = relationship("CheckIn", back_populates="baggage")

    def __repr__(self):
        return f"<Baggage {self.id} ({self.weight_kg}kg)>"

