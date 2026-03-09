"""
Seat SQLAlchemy models.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from src.config.database import Base


class SeatStatus(str, enum.Enum):
    """Seat status enum."""
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    CONFIRMED = "CONFIRMED"


class SeatClass(str, enum.Enum):
    """Seat class enum."""
    ECONOMY = "economy"
    BUSINESS = "business"
    FIRST = "first"


class Seat(Base):
    """Seat database model."""

    __tablename__ = "seats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    seat_number = Column(String(4), nullable=False)
    seat_class = Column(String(20), default=SeatClass.ECONOMY.value)
    status = Column(String(20), default=SeatStatus.AVAILABLE.value, nullable=False)

    # Hold information
    held_by = Column(UUID(as_uuid=True), ForeignKey("passengers.id"), nullable=True)
    held_at = Column(DateTime, nullable=True)
    hold_expires_at = Column(DateTime, nullable=True)

    # Confirmation information
    confirmed_by = Column(UUID(as_uuid=True), ForeignKey("passengers.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    flight = relationship("Flight", back_populates="seats")
    holder = relationship("Passenger", foreign_keys=[held_by], lazy="selectin")
    confirmer = relationship("Passenger", foreign_keys=[confirmed_by], lazy="selectin")
    state_history = relationship("SeatStateHistory", back_populates="seat", lazy="selectin")

    # Indexes for performance
    __table_args__ = (
        Index("idx_seats_flight_id", "flight_id"),
        Index("idx_seats_status", "status"),
        Index("idx_seats_flight_status", "flight_id", "status"),
        Index("idx_seats_hold_expires", "hold_expires_at", postgresql_where=(status == SeatStatus.HELD.value)),
        {"extend_existing": True}
    )

    def __repr__(self):
        return f"<Seat {self.seat_number} ({self.status})>"

    def is_available(self) -> bool:
        """Check if seat is available for selection."""
        return self.status == SeatStatus.AVAILABLE.value

    def is_held(self) -> bool:
        """Check if seat is currently held."""
        return self.status == SeatStatus.HELD.value

    def is_confirmed(self) -> bool:
        """Check if seat is confirmed."""
        return self.status == SeatStatus.CONFIRMED.value

    def is_held_by(self, passenger_id: uuid.UUID) -> bool:
        """Check if seat is held by a specific passenger."""
        return self.is_held() and self.held_by == passenger_id


class SeatStateHistory(Base):
    """Audit table for seat state changes."""

    __tablename__ = "seat_state_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seat_id = Column(UUID(as_uuid=True), ForeignKey("seats.id"), nullable=False)
    previous_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("passengers.id"), nullable=True)
    change_reason = Column(String(100), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    seat = relationship("Seat", back_populates="state_history")

    __table_args__ = (
        Index("idx_seat_history_seat_id", "seat_id"),
        Index("idx_seat_history_changed_at", "changed_at"),
    )

    def __repr__(self):
        return f"<SeatStateHistory {self.seat_id}: {self.previous_status} -> {self.new_status}>"

