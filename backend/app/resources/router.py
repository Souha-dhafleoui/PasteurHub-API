from fastapi import APIRouter
from app.resources import assessments, vaccines, cases, destinations

router = APIRouter(prefix="/resources")

router.include_router(assessments.router)
router.include_router(vaccines.router)
router.include_router(cases.router)
router.include_router(destinations.router)
