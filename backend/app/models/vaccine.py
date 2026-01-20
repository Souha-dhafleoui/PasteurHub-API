from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Vaccine(Base):
    __tablename__ = "vaccines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)


    # NEW: price info (from Institut Pasteur official “vaccins pratiqués” page)
    price_tnd = Column(Numeric(10, 3), nullable=True)  # ex: 92.000
    currency = Column(String(8), nullable=False, default="TND")
    price_source_url = Column(String, nullable=True)
    price_updated_at = Column(DateTime, nullable=True)

    # optional relationship (not required)
    destination_links = relationship(
        "DestinationVaccine",
        back_populates="vaccine",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def set_price(self, price_tnd, source_url: str):
        self.price_tnd = price_tnd
        self.currency = "TND"
        self.price_source_url = source_url
        self.price_updated_at = datetime.utcnow()
