from pydantic import BaseModel, Field
from typing import Optional

class CaseCreate(BaseModel):
    problem_text: str = Field(min_length=5)
    scenario_type: Optional[str] = Field(default=None, max_length=50)
    vaccine_id: int = Field(ge=1)

class CaseOut(BaseModel):
    id: int
    problem_text: str
    scenario_type: Optional[str]
    vaccine_id: int

    class Config:
        from_attributes = True