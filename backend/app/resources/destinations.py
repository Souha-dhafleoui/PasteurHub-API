from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.destination import Destination
from app.models.vaccine import Vaccine
from app.models.destination_vaccine import DestinationVaccine

from app.schemas.travel import (
    DestinationOut,
    DestinationRecommendationsOut,
    DestinationVaccineOut,
)

from app.services.travel_scraper import scrape_country_recommendations


router = APIRouter(prefix="/destinations", tags=["destinations"])


def _map_scraped_key_to_ipt_vaccine_names(scraped_key: str) -> List[str]:
    """
    Map Pasteur.fr scraped vaccine categories to your IPT Tunisia vaccine catalog
    (short English names — your choice A).
    """
    mapping = {
        "yellow_fever": ["Yellow Fever (single-dose)", "Yellow Fever (multi-dose)"],
        "hepatitis_a": ["Hepatitis A (adult)"],
        "hepatitis_b": ["Hepatitis B (adult)"],
        "typhoid": ["Typhoid"],
        "rabies": ["Rabies vaccine"],
        "polio": ["Polio (injectable) - Imovax Polio"],
        "meningitis": ["Meningococcal ACYW135"],
        "dt": ["Diphtheria-Tetanus (adult)", "DTP (adult) - Dultavax", "DTaP-IPV - Tetraxim"],
        "mmr": ["MMR - Priorix"],
        "pneumo": ["Pneumococcal - Prevenar13", "Pneumococcal - Pneumovax"],
    }
    return mapping.get(scraped_key, [])


@router.get("", response_model=List[DestinationOut])
def list_destinations(
    q: Optional[str] = Query(default=None, description="Search by destination name"),
    db: Session = Depends(get_db),
):
    query = db.query(Destination)

    if q:
        query = query.filter(Destination.name.ilike(f"%{q}%"))

    items = query.order_by(Destination.name).all()
    return [DestinationOut(id=d.id, name=d.name, group_code=d.group_code) for d in items]


@router.get("/{destination_id}/recommendations", response_model=DestinationRecommendationsOut)
def get_destination_recommendations(destination_id: int, db: Session = Depends(get_db)):
    dest = db.query(Destination).filter(Destination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")

    # ---------------------------
    # 1) Return cached (mapped) recommendations if present
    # ---------------------------
    cached = (
        db.query(DestinationVaccine, Vaccine)
        .join(Vaccine, Vaccine.id == DestinationVaccine.vaccine_id)
        .filter(DestinationVaccine.destination_id == dest.id)
        .all()
    )

    if cached:
        recs: List[DestinationVaccineOut] = []
        for link, v in cached:
            price = float(v.price_tnd) if v.price_tnd is not None else None
            status = "available" if price is not None else "unknown"

            recs.append(
                DestinationVaccineOut(
                    vaccine_name=v.name,
                    requirement_level=link.requirement_level,
                    notes=link.notes,
                    available_in_ipt=True,
                    status=status,
                    price_tnd=price,
                    currency=v.currency,
                    price_source_url=v.price_source_url,
                )
            )

        return DestinationRecommendationsOut(
            destination=DestinationOut(id=dest.id, name=dest.name, group_code=dest.group_code),
            recommendations=recs,
            source_url=dest.source_url,
            last_updated=None,
        )

    # ---------------------------
    # 2) Otherwise: live scrape Pasteur.fr and map to IPT catalog
    # ---------------------------
    if not dest.source_url:
        raise HTTPException(status_code=400, detail="Destination has no source_url to scrape")

    try:
        scraped = scrape_country_recommendations(dest.source_url)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch destination recommendations from source")

    last_updated = scraped.get("last_updated")
    items = scraped.get("items", []) or []

    created: List[DestinationVaccineOut] = []

    for it in items:
        key = (it.get("key") or "").strip()
        label_fr = (it.get("label_fr") or "Unknown vaccine").strip()
        requirement_level = (it.get("requirement_level") or "recommended").strip().lower()

        ipt_names = _map_scraped_key_to_ipt_vaccine_names(key)

        # If not mapped -> return as unavailable (not priced / not recognized at IPT)
        if not ipt_names:
            created.append(
                DestinationVaccineOut(
                    vaccine_name=f"{label_fr} (not priced at IPT)",
                    requirement_level=requirement_level,
                    notes="Listed on Pasteur.fr, but not recognized/mapped to Institut Pasteur de Tunis price list.",
                    available_in_ipt=False,
                    status="unavailable",
                    price_tnd=None,
                    currency="TND",
                    price_source_url=None,
                )
            )
            continue

        # If mapped -> return each mapped IPT vaccine; cache only mapped items
        for ipt_vaccine_name in ipt_names:
            v = db.query(Vaccine).filter(Vaccine.name == ipt_vaccine_name).first()

            # Mapped but missing in DB => show unavailable (should be rare if seed is correct)
            if not v:
                created.append(
                    DestinationVaccineOut(
                        vaccine_name=f"{ipt_vaccine_name} (missing in IPT DB)",
                        requirement_level=requirement_level,
                        notes="Mapped from Pasteur.fr, but not found in IPT database.",
                        available_in_ipt=False,
                        status="unavailable",
                        price_tnd=None,
                        currency="TND",
                        price_source_url=None,
                    )
                )
                continue

            # Cache the mapped link
            exists = (
                db.query(DestinationVaccine)
                .filter(
                    DestinationVaccine.destination_id == dest.id,
                    DestinationVaccine.vaccine_id == v.id,
                )
                .first()
            )
            if not exists:
                db.add(
                    DestinationVaccine(
                        destination_id=dest.id,
                        vaccine_id=v.id,
                        requirement_level=requirement_level,
                        notes="Mapped from Pasteur.fr; priced locally using Institut Pasteur de Tunis official price list.",
                        source_url=dest.source_url,
                    )
                )
                db.commit()

            price = float(v.price_tnd) if v.price_tnd is not None else None
            status = "available" if price is not None else "unknown"

            created.append(
                DestinationVaccineOut(
                    vaccine_name=v.name,
                    requirement_level=requirement_level,
                    notes="Mapped from Pasteur.fr; priced locally using Institut Pasteur de Tunis official price list.",
                    available_in_ipt=True,
                    status=status,
                    price_tnd=price,
                    currency=v.currency,
                    price_source_url=v.price_source_url,
                )
            )

    return DestinationRecommendationsOut(
        destination=DestinationOut(id=dest.id, name=dest.name, group_code=dest.group_code),
        recommendations=created,
        source_url=dest.source_url,
        last_updated=last_updated,
    )
