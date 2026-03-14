from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.login_schema import AppleLoginRequest, LoginRequest, TokenResponse
from app.models.user import User
from app.database.deps import get_db
from app.core.settings import settings
from app.security.apple_auth import verify_apple_identity_token
from app.security.auth import verify_password, create_access_token, hash_password, get_current_user
from app.schemas.user_schema import UserResponse

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

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

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Apple no envio email. Reintenta con una cuenta nueva o provee email.",
        )

    user = db.query(User).filter(User.apple_sub == apple_sub).first()

    if not user:
        user = db.query(User).filter(User.email == email).first()

        if user is not None and user.apple_sub is not None and user.apple_sub != apple_sub:
            raise HTTPException(status_code=409, detail="Cuenta Apple no coincide")

        if not user:
            user = User(
                email=email,
                password=hash_password(apple_sub),
                apple_sub=apple_sub,
                is_email_verified=True,
            )
            db.add(user)
        else:
            setattr(user, "apple_sub", apple_sub)
            setattr(user, "is_email_verified", True)

        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me", response_model=UserResponse)
def auth_me(current_user: User = Depends(get_current_user)):
    return current_user
