"""
Passenger SQLAlchemy model.
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.config.database import Base


class Passenger(Base):
    """Passenger database model."""

    __tablename__ = "passengers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    booking_reference = Column(String(10), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    checkins = relationship("CheckIn", back_populates="passenger", lazy="selectin")

    def __repr__(self):
        return f"<Passenger {self.first_name} {self.last_name}>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

