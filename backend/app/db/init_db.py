from app.db.base import Base
from app.db.session import engine

from app.models.user import User  # noqa: F401
from app.models.vaccine import Vaccine  # noqa: F401
from app.models.case import Case  # noqa: F401
from app.models.destination import Destination  # noqa: F401
from app.models.destination_vaccine import DestinationVaccine  # noqa: F401


def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")


if __name__ == "__main__":
    init_db()
