from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.assessment import AssessmentIn, AssessmentOut, MatchOut
from app.services.cbr import find_similar_cases

router = APIRouter(prefix="/assessments", tags=["assessments"])

TOP_K = 2  # keep results small & stable


@router.post("", response_model=AssessmentOut)
def assess(payload: AssessmentIn, db: Session = Depends(get_db)):
    matches = find_similar_cases(
        db=db,
        query_text=payload.problem_text,
        scenario_type=payload.scenario_type,
        top_k=TOP_K,
    )
    return {"matches": [MatchOut(**m) for m in matches]}
