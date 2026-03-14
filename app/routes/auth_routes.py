from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.schemas.login_schema import AppleLoginRequest, LoginRequest, TokenResponse
from app.models.user import User
from app.database.deps import get_db
from app.core.settings import settings
from app.security.apple_auth import verify_apple_identity_token
from app.security.auth import verify_password, create_access_token, hash_password, get_current_user
from app.schemas.user_schema import UserResponse

router = APIRouter()


def _candidate_nicknames_from_email(email: str | None) -> list[str]:
    if not email or "@" not in email:
        return []

    base = email.split("@", 1)[0].strip().lower()
    cleaned = "".join(ch for ch in base if ch.isalnum() or ch == "_")
    if len(cleaned) < 3:
        cleaned = f"user_{cleaned}" if cleaned else "user"
    cleaned = cleaned[:24]
    return [cleaned, f"{cleaned[:20]}_ios", f"{cleaned[:20]}_app"]


def _resolve_unique_nickname(db: Session, preferred: str | None, email: str | None) -> str:
    options = []
    if preferred:
        options.append(preferred.strip().lower())
    options.extend(_candidate_nicknames_from_email(email))

    for option in options:
        if len(option) < 3:
            continue
        exists = db.query(User).filter(User.nickname == option).first()
        if not exists:
            return option

    seed = "user"
    suffix = 1
    while True:
        candidate = f"{seed}_{suffix}"
        if db.query(User).filter(User.nickname == candidate).first() is None:
            return candidate
        suffix += 1

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == data.email.lower()).first()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/auth/apple", response_model=TokenResponse)
def login_with_apple(data: AppleLoginRequest, db: Session = Depends(get_db)):
    try:
        claims = verify_apple_identity_token(data.identity_token, settings.apple_audience)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    apple_sub = claims.get("sub")
    email = claims.get("email") or data.email

    if not apple_sub:
        raise HTTPException(status_code=400, detail="Apple token sin subject")

    user = db.query(User).filter(User.apple_sub == apple_sub).first()

    if user:
        current_nickname = getattr(user, "nickname", None)
        current_email = getattr(user, "email", None)
        if data.nickname and not current_nickname:
            setattr(user, "nickname", _resolve_unique_nickname(db, data.nickname, current_email))
            db.commit()
            db.refresh(user)

        token = create_access_token({"sub": user.email})
        return {"access_token": token, "token_type": "bearer"}

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Apple no envio email. Reintenta con una cuenta nueva o provee email.",
        )

    user = db.query(User).filter(func.lower(User.email) == email.lower()).first()

    if user is not None and user.apple_sub is not None and user.apple_sub != apple_sub:
        raise HTTPException(status_code=409, detail="Cuenta Apple no coincide")

    if not user:
        user = User(
            email=email,
            nickname=_resolve_unique_nickname(db, data.nickname, email),
            password=hash_password(apple_sub),
            apple_sub=apple_sub,
            is_email_verified=True,
        )
        db.add(user)
    else:
        setattr(user, "apple_sub", apple_sub)
        setattr(user, "is_email_verified", True)
        current_nickname = getattr(user, "nickname", None)
        current_email = getattr(user, "email", None)
        if not current_nickname:
            setattr(user, "nickname", _resolve_unique_nickname(db, data.nickname, current_email))

    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me", response_model=UserResponse)
def auth_me(current_user: User = Depends(get_current_user)):
    return current_user
