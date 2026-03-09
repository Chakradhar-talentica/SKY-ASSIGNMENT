"""
Flight SQLAlchemy model.
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.config.database import Base


class Flight(Base):
    """Flight database model."""

    __tablename__ = "flights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_number = Column(String(10), nullable=False, index=True)
    departure_airport = Column(String(3), nullable=False)
    arrival_airport = Column(String(3), nullable=False)
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)
    aircraft_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    seats = relationship("Seat", back_populates="flight", lazy="selectin")
    checkins = relationship("CheckIn", back_populates="flight", lazy="selectin")

    def __repr__(self):
        return f"<Flight {self.flight_number}>"

