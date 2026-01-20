from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class DestinationVaccine(Base):
    __tablename__ = "destination_vaccines"

    destination_id = Column(
        Integer,
        ForeignKey("destinations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vaccine_id = Column(
        Integer,
        ForeignKey("vaccines.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # "required" or "recommended"
    requirement_level = Column(String(20), nullable=False)
    notes = Column(String, nullable=True)
    source_url = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    destination = relationship("Destination", back_populates="vaccines")
    vaccine = relationship("Vaccine", back_populates="destination_links")
