from __future__ import annotations

import os
import sys
from decimal import Decimal
from datetime import datetime
from typing import List

# Fix Python path for script execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text

from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal
from app.models.user import User
from app.models.vaccine import Vaccine
from app.models.case import Case
from app.models.destination import Destination
from app.models.destination_vaccine import DestinationVaccine

from app.services.travel_scraper import fetch_country_index

IPT_PRICE_SOURCE_URL = "https://pasteur.tn/vp"

OFFICIAL_IPT_VACCINES: List[dict] = [
    {"name": "Yellow Fever (multi-dose)", "price_tnd": None, "note": "Marked as not available on IPT website."},
    {"name": "Yellow Fever (single-dose)", "price_tnd": Decimal("92.000"), "note": None},
    {"name": "Hepatitis A (adult)", "price_tnd": Decimal("100.000"), "note": None},
    {"name": "Typhoid", "price_tnd": Decimal("50.000"), "note": None},
    {"name": "Diphtheria-Tetanus (adult)", "price_tnd": Decimal("18.000"), "note": None},
    {"name": "Rabies vaccine", "price_tnd": Decimal("31.943"), "note": None},
    {"name": "DTP (adult) - Dultavax", "price_tnd": Decimal("75.000"), "note": None},
    {"name": "Polio (injectable) - Imovax Polio", "price_tnd": Decimal("45.000"), "note": None},
    {"name": "MMR - Priorix", "price_tnd": Decimal("55.000"), "note": None},
    {"name": "Hepatitis B (adult)", "price_tnd": Decimal("20.000"), "note": None},
    {"name": "Meningococcal ACYW135", "price_tnd": Decimal("130.000"), "note": None},
    {"name": "DTaP-IPV - Tetraxim", "price_tnd": Decimal("80.000"), "note": None},
    {"name": "Pneumococcal - Prevenar13", "price_tnd": Decimal("240.000"), "note": None},
    {"name": "Pneumococcal - Pneumovax", "price_tnd": Decimal("120.000"), "note": None},
    {"name": "Tuberculin skin test (PPD)", "price_tnd": Decimal("55.000"), "note": None},
    {"name": "International certificate duplicate (service)", "price_tnd": Decimal("10.000"), "note": "Service (not a vaccine)."},
]

SCENARIO_TO_VACCINE = {
    "bite": "Rabies vaccine",
    "wound": "Diphtheria-Tetanus (adult)",
    "fever": "Yellow Fever (single-dose)",
    "gastro": "Typhoid",
    "food_water": "Hepatitis A (adult)",
    "risk": "Hepatitis B (adult)",
    "polio": "Polio (injectable) - Imovax Polio",
    "crowd": "Meningococcal ACYW135",
    "childhood": "MMR - Priorix",
    "respiratory": "Pneumococcal - Prevenar13",
}


def maybe_reset(db):
    """
    DEV ONLY.
    If RESET_DB=1, wipe data tables (keeps alembic_version).
    """
    if os.getenv("RESET_DB", "0") != "1":
        return

    db.execute(text("DELETE FROM destination_vaccines;"))
    db.execute(text("DELETE FROM destinations;"))
    db.execute(text("DELETE FROM cases;"))
    db.execute(text("DELETE FROM vaccines;"))
    db.execute(text("DELETE FROM users;"))
    db.commit()


def seed_staff_users(db):
    """
    Seed ONLY these two staff accounts (role=admin):

    - souha@gmail.com / souha123
    - doctor@gmail.com / doctor456

    Idempotent: creates if missing, updates role, updates password if changed.
    """
    staff = [
        ("souha@gmail.com", "souha123", "admin"),
        ("doctor@gmail.com", "doctor456", "admin"),
    ]

    created = 0
    updated = 0

    for username, plain_pw, role in staff:
        u = db.query(User).filter(User.username == username).first()

        if not u:
            u = User(
                username=username,
                password_hash=hash_password(plain_pw),
                role=role,
            )
            db.add(u)
            created += 1
            continue

        changed = False

        # Keep role in sync
        if u.role != role:
            u.role = role
            changed = True

        # Update password if the script value differs
        # (we verify against the existing hash; if mismatch, regenerate)
        if not verify_password(plain_pw, u.password_hash):
            u.password_hash = hash_password(plain_pw)
            changed = True

        if changed:
            updated += 1

    db.commit()
    print(f"✅ Seeded staff users: created={created}, updated={updated}, total={db.query(User).count()}")


def upsert_ipt_vaccines(db):
    now = datetime.utcnow()

    for item in OFFICIAL_IPT_VACCINES:
        name = item["name"]
        price = item["price_tnd"]
        note = item.get("note")

        v = db.query(Vaccine).filter(Vaccine.name == name).first()
        if not v:
            v = Vaccine(name=name)

        v.description = "Official Institut Pasteur de Tunis item (English)." + (f" {note}" if note else "")
        v.currency = "TND"
        v.price_source_url = IPT_PRICE_SOURCE_URL
        v.price_updated_at = now
        v.price_tnd = price

        db.add(v)

    db.commit()


def seed_destinations_from_pasteur_fr(db):
    """
    Seeds ALL destinations from Pasteur.fr JSON index.
    """
    items = fetch_country_index(timeout=30)

    added = 0
    for it in items:
        name = it["name"]
        url = it["url"]

        exists = db.query(Destination).filter(Destination.source_url == url).first()
        if exists:
            continue

        dest = Destination(name=name, group_code="PASTEUR_FR", source_url=url)
        db.add(dest)
        added += 1

    db.commit()
    print(f"Seeded destinations from Pasteur.fr: +{added}")


def seed_symptom_cases(db):
    """
    Seeds demo cases for CBR.
    """
    added = 0
    for scenario, vaccine_name in SCENARIO_TO_VACCINE.items():
        vaccine = db.query(Vaccine).filter(Vaccine.name == vaccine_name).first()
        if not vaccine:
            continue

        prompts = [
            f"{scenario}: patient needs advice",
            f"{scenario}: exposure and vaccination needed",
            f"{scenario}: risk assessment and prevention",
            f"{scenario}: what vaccine is recommended?",
            f"{scenario}: consult travel clinic recommendation",
        ]

        for p in prompts:
            exists = db.query(Case).filter(Case.problem_text == p).first()
            if exists:
                continue

            c = Case(problem_text=p, scenario_type=scenario, vaccine_id=vaccine.id)
            db.add(c)
            added += 1

    db.commit()
    print(f"Seeded symptom cases: +{added} (total now {db.query(Case).count()})")


def seed_destination_vaccine_links(db):
    """
    Simple demo links: attach a few vaccines to a few destinations.
    """
    destinations = db.query(Destination).limit(20).all()
    vaccines = db.query(Vaccine).limit(8).all()

    if not destinations or not vaccines:
        return

    added = 0
    for d in destinations[:10]:
        for v in vaccines[:4]:
            exists = (
                db.query(DestinationVaccine)
                .filter(
                    DestinationVaccine.destination_id == d.id,
                    DestinationVaccine.vaccine_id == v.id,
                )
                .first()
            )
            if exists:
                continue

            link = DestinationVaccine(
                destination_id=d.id,
                vaccine_id=v.id,
                requirement_level="recommended",
                notes="Demo seeded recommendation",
            )
            db.add(link)
            added += 1

    db.commit()
    print(f"Seeded destination-vaccine links: +{added}")


def main():
    db = SessionLocal()
    try:
        maybe_reset(db)

        seed_staff_users(db)
        upsert_ipt_vaccines(db)
        seed_destinations_from_pasteur_fr(db)
        seed_symptom_cases(db)
        seed_destination_vaccine_links(db)

        print("Seeding done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
