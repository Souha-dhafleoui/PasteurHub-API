from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)

    # The "problem" text that will be used for similarity search
    problem_text = Column(Text, nullable=False)

    # Simple metadata for filtering/boosting
    scenario_type = Column(String(50), nullable=True)

    # Solution link
    vaccine_id = Column(Integer, ForeignKey("vaccines.id", ondelete="RESTRICT"), nullable=False)

    vaccine = relationship("Vaccine")