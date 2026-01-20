from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Destination(Base):
    __tablename__ = "destinations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False, index=True)

    # e.g. "GROUPE_II" or "ARABIE_SAOUDITE"
    group_code = Column(String(50), nullable=True)

    # URL of the official PDF used
    source_url = Column(String, nullable=True)

    vaccines = relationship(
        "DestinationVaccine",
        back_populates="destination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
