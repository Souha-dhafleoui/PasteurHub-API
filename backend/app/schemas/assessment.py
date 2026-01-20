from typing import List, Optional
from pydantic import BaseModel, Field


class AssessmentIn(BaseModel):
    problem_text: str = Field(..., min_length=5, examples=["Fever after mosquito bites in a tropical area"])
    scenario_type: Optional[str] = Field(
        default=None,
        examples=["fever"],
        description="Optional: fever, gastro, risk, wound, bite, crowd"
    )


class MatchOut(BaseModel):
    case_id: int
    score: float

    problem_text: str
    scenario_type: Optional[str]

    vaccine_id: int
    vaccine_name: str
    vaccine_description: Optional[str] = None

    semantic_score: float
    context_score: float
    scenario_match: bool


class AssessmentOut(BaseModel):
    matches: List[MatchOut]