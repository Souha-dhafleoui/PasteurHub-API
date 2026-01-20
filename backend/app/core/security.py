import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User

JWT_SECRET_ENV = "JWT_SECRET_KEY"
JWT_ALGORITHM_ENV = "JWT_ALGORITHM"
JWT_EXPIRE_MINUTES_ENV = "JWT_EXPIRE_MINUTES"

# Swagger will show the "Authorize" dialog for Bearer auth.
# It will send: Authorization: Bearer <token>
bearer_scheme = HTTPBearer(auto_error=False)

# password hashing settings (PBKDF2, no extra deps)
_PBKDF2_NAME = "sha256"
_PBKDF2_ITERS = 210_000
_SALT_BYTES = 16


def _get_jwt_config() -> Tuple[str, str, int]:
    secret = os.getenv(JWT_SECRET_ENV)
    if not secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY is not configured")

    alg = os.getenv(JWT_ALGORITHM_ENV, "HS256")

    try:
        exp_minutes = int(os.getenv(JWT_EXPIRE_MINUTES_ENV, "240"))
    except ValueError:
        exp_minutes = 240

    exp_minutes = max(1, min(exp_minutes, 60 * 24 * 30))  # 1 min .. 30 days
    return secret, alg, exp_minutes


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def hash_password(password: str) -> str:
    """
    Returns:
      pbkdf2_sha256$210000$<salt_b64>$<dk_b64>
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(_PBKDF2_NAME, password.encode("utf-8"), salt, _PBKDF2_ITERS)
    return f"pbkdf2_sha256${_PBKDF2_ITERS}${_b64e(salt)}${_b64e(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters_s, salt_b64, dk_b64 = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = _b64d(salt_b64)
        expected = _b64d(dk_b64)
        dk = hashlib.pbkdf2_hmac(_PBKDF2_NAME, password.encode("utf-8"), salt, iters)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def authenticate_user_db(db: Session, username: str, password: str) -> str | None:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user.role


def create_access_token(subject: str, role: str = "admin") -> str:
    secret, alg, exp_minutes = _get_jwt_config()

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=alg)


def decode_token(token: str) -> Dict[str, Any]:
    secret, alg, _ = _get_jwt_config()
    try:
        payload = jwt.decode(token, secret, algorithms=[alg])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return payload


def _normalize_token(token: str) -> str:
    """
    Handles cases where the user pastes 'Bearer <token>' into Swagger,
    and Swagger then sends 'Bearer Bearer <token>'.
    """
    t = token.strip()
    if not t:
        raise HTTPException(status_code=401, detail="Missing token")
    if t.lower().startswith("bearer "):
        return t.split(None, 1)[1].strip()
    return t


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # creds.scheme should be "Bearer" normally, creds.credentials is the token part.
    token = _normalize_token(creds.credentials)
    claims = decode_token(token)

    # Ensure user still exists; take role from DB (not just token)
    user = db.query(User).filter(User.username == claims["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"sub": user.username, "role": user.role}


def require_admin_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user
