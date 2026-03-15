from datetime import datetime, timedelta

import base64
import hmac
import hashlib
import os
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.database.deps import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

PBKDF2_ITERATIONS = 600000

try:
    import bcrypt  # type: ignore
except Exception:
    bcrypt = None


def _normalize_password_input(password: str) -> bytes:
    """Normalize password input before hashing to keep behavior consistent."""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str):
    normalized = _normalize_password_input(password)
    salt = os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        normalized,
        salt,
        PBKDF2_ITERATIONS,
    )
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_hash = base64.b64encode(derived_key).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${encoded_salt}${encoded_hash}"


def verify_password(plain_password, hashed_password):
    try:
        normalized = _normalize_password_input(plain_password)
        if hashed_password.startswith("pbkdf2_sha256$"):
            _, iterations, encoded_salt, encoded_hash = hashed_password.split("$", 3)
            derived_key = hashlib.pbkdf2_hmac(
                "sha256",
                normalized,
                base64.b64decode(encoded_salt.encode("ascii")),
                int(iterations),
            )
            return hmac.compare_digest(
                base64.b64encode(derived_key).decode("ascii"),
                encoded_hash,
            )

        if bcrypt is None:
            return False

        stored_hash = hashed_password.encode("utf-8")
        if bcrypt.checkpw(normalized, stored_hash):
            return True

        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
        ) from exc


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    subject = payload.get("sub")

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    user = db.query(User).filter(User.email == subject, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )

    return user
