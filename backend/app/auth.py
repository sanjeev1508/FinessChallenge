"""Password hashing and JWT authentication dependencies."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from . import config
from .database import get_db

_password_hash = PasswordHash.recommended()
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    db: Session


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


def create_access_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expires}, config.JWT_SECRET_KEY, algorithm="HS256")


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None:
        raise _unauthorized("Authentication is required.")
    try:
        payload = jwt.decode(credentials.credentials, config.JWT_SECRET_KEY, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise _unauthorized("Access token is invalid or expired.") from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise _unauthorized("Access token is invalid or expired.")
    # Defer DB reads to the route so authentication does not hold a pooled connection while waiting for a worker.
    return AuthContext(user_id=user_id, db=db)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail=message, headers={"WWW-Authenticate": "Bearer"})
