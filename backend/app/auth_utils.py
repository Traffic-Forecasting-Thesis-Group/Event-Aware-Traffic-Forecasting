from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

# ── Configuration ────────────────────────────────────────────────────────
# Set a real secret in your backend .env, e.g.:
#   AUTH_SECRET_KEY=some-long-random-string
SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "dev-only-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """subject is typically the user's email or id, stored in the 'sub' claim."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Returns the 'sub' claim (e.g. user email) if valid, else None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
