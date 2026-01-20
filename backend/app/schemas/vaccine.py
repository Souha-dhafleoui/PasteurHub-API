from pydantic import BaseModel, Field
from typing import Optional


class VaccineCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None

    # allow manual price updates too (admin endpoint)
    price_tnd: Optional[float] = None


class VaccineOut(BaseModel):
    id: int
    name: str
    description: Optional[str]

    price_tnd: Optional[float] = None
    currency: Optional[str] = None
    price_source_url: Optional[str] = None

    class Config:
        from_attributes = True
