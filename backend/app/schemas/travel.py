from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


class DestinationOut(BaseModel):
    id: int
    name: str
    group_code: Optional[str] = None


class DestinationVaccineOut(BaseModel):
    vaccine_name: str
    requirement_level: str
    notes: Optional[str] = None

    # Tunisia value-add fields:
    available_in_ipt: bool
    status: str  # "available" | "unavailable" | "unknown"
    price_tnd: Optional[float] = None
    currency: Optional[str] = "TND"
    price_source_url: Optional[str] = None


class DestinationRecommendationsOut(BaseModel):
    destination: DestinationOut
    recommendations: List[DestinationVaccineOut]
    source_url: Optional[str] = None
    last_updated: Optional[str] = None
