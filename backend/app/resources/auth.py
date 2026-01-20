import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import authenticate_user_db, create_access_token
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    role = authenticate_user_db(db, payload.username, payload.password)
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    jwt_token = create_access_token(subject=payload.username, role=role)
    expires_in = int(os.getenv("JWT_EXPIRE_MINUTES", "240"))
    return TokenResponse(access_token=jwt_token, token_type="bearer", expires_in_minutes=expires_in)
