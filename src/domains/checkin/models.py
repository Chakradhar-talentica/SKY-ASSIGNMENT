"""
CheckIn SQLAlchemy model.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from src.config.database import Base


class CheckInStatus(str, enum.Enum):
    """Check-in status enum."""
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_PAYMENT = "WAITING_FOR_PAYMENT"
    COMPLETED = "COMPLETED"


class CheckIn(Base):
    """Check-in database model."""

    __tablename__ = "checkins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    passenger_id = Column(UUID(as_uuid=True), ForeignKey("passengers.id"), nullable=False)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    seat_id = Column(UUID(as_uuid=True), ForeignKey("seats.id"), nullable=True)
    status = Column(String(30), default=CheckInStatus.IN_PROGRESS.value, nullable=False)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    passenger = relationship("Passenger", back_populates="checkins", lazy="selectin")
    flight = relationship("Flight", back_populates="checkins", lazy="selectin")
    seat = relationship("Seat", lazy="selectin")
    baggage = relationship("Baggage", back_populates="checkin", lazy="selectin")
    payments = relationship("Payment", back_populates="checkin", lazy="selectin")

    # Indexes
    __table_args__ = (
        Index("idx_checkin_passenger_flight", "passenger_id", "flight_id", unique=True),
        Index("idx_checkin_status", "status"),
    )

    def __repr__(self):
        return f"<CheckIn {self.id} ({self.status})>"

    def is_in_progress(self) -> bool:
        return self.status == CheckInStatus.IN_PROGRESS.value

    def is_waiting_for_payment(self) -> bool:
        return self.status == CheckInStatus.WAITING_FOR_PAYMENT.value

    def is_completed(self) -> bool:
        return self.status == CheckInStatus.COMPLETED.value

