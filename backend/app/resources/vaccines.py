from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import require_admin_user
from app.db.session import get_db
from app.models.vaccine import Vaccine
from app.schemas.vaccine import VaccineCreate, VaccineOut

from app.models.case import Case
from app.models.destination_vaccine import DestinationVaccine

router = APIRouter(prefix="/vaccines", tags=["vaccines"])

# Age-related fields were removed from the API.
VaccineSortBy = Literal["name", "id", "price_tnd"]
SortDir = Literal["asc", "desc"]


@router.get("", response_model=list[VaccineOut])
def list_vaccines(
    q: str | None = Query(default=None, description="Optional search term (matches name or description)"),
    min_price_tnd: float | None = Query(default=None, ge=0, description="Optional minimum price in TND"),
    max_price_tnd: float | None = Query(default=None, ge=0, description="Optional maximum price in TND"),
    sort_by: VaccineSortBy = Query(default="name", description="Sort field"),
    sort_dir: SortDir = Query(default="asc", description="Sort direction"),
    db: Session = Depends(get_db),
):
    query = db.query(Vaccine)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Vaccine.name.ilike(like), Vaccine.description.ilike(like)))

    if min_price_tnd is not None:
        query = query.filter(Vaccine.price_tnd.is_not(None), Vaccine.price_tnd >= min_price_tnd)

    if max_price_tnd is not None:
        query = query.filter(Vaccine.price_tnd.is_not(None), Vaccine.price_tnd <= max_price_tnd)

    sort_map = {"id": Vaccine.id, "name": Vaccine.name, "price_tnd": Vaccine.price_tnd}
    col = sort_map[sort_by]
    query = query.order_by(col.desc() if sort_dir == "desc" else col.asc())

    return query.all()



@router.post(
    "",
    response_model=VaccineOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(require_admin_user)],
)
def create_vaccine(payload: VaccineCreate, db: Session = Depends(get_db)):
    exists = db.query(Vaccine).filter(Vaccine.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="Vaccine with this name already exists")

    v = Vaccine(**payload.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v

@router.delete(
    "/{vaccine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Security(require_admin_user)],
)
def delete_vaccine(vaccine_id: int, db: Session = Depends(get_db)):
    v = db.query(Vaccine).filter(Vaccine.id == vaccine_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vaccine not found")

    # Prevent orphan references (cases and destination links)
    used_in_cases = db.query(Case).filter(Case.vaccine_id == vaccine_id).first() is not None
    used_in_destinations = (
        db.query(DestinationVaccine).filter(DestinationVaccine.vaccine_id == vaccine_id).first() is not None
    )

    if used_in_cases or used_in_destinations:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete vaccine because it is referenced by cases or destination recommendations",
        )

    db.delete(v)
    db.commit()
    return

