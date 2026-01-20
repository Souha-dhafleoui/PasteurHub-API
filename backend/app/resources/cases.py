from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import require_admin_user
from app.db.session import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseOut

router = APIRouter(prefix="/cases", tags=["cases"])

CaseSortBy = Literal["id", "scenario_type", "vaccine_id"]
SortDir = Literal["asc", "desc"]


@router.get("", response_model=list[CaseOut])
def list_cases(
    q: str | None = Query(default=None, description="Optional search term (matches problem_text)"),
    scenario_type: str | None = Query(default=None, description="Optional scenario filter"),
    vaccine_id: int | None = Query(default=None, ge=1, description="Optional vaccine_id filter"),
    sort_by: CaseSortBy = Query(default="id", description="Sort field"),
    sort_dir: SortDir = Query(default="desc", description="Sort direction"),
    db: Session = Depends(get_db),
):
    query = db.query(Case)

    if q:
        query = query.filter(Case.problem_text.ilike(f"%{q}%"))

    if scenario_type:
        query = query.filter(Case.scenario_type == scenario_type)

    if vaccine_id is not None:
        query = query.filter(Case.vaccine_id == vaccine_id)

    sort_map = {
        "id": Case.id,
        "scenario_type": Case.scenario_type,
        "vaccine_id": Case.vaccine_id,
    }
    col = sort_map[sort_by]
    query = query.order_by(col.desc() if sort_dir == "desc" else col.asc())

    return query.all()



@router.post(
    "",
    response_model=CaseOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(require_admin_user)],
)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    c = Case(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Security(require_admin_user)],
)
def delete_case(case_id: int, db: Session = Depends(get_db)):
    c = db.query(Case).filter(Case.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(c)
    db.commit()
    return None
