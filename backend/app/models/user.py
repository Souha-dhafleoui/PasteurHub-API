from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(500), nullable=False)

    # for your demo: keep roles simple: "admin" (you can add "viewer" later)
    role = Column(String(50), nullable=False, default="admin")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
