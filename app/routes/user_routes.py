from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.schemas.user_schema import UserCreate, UserResponse
from app.models.user import User
from app.database.deps import get_db
from app.security.auth import hash_password

router = APIRouter()

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(func.lower(User.email) == user.email.lower()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_nickname = db.query(User).filter(User.nickname == user.nickname).first()
    if existing_nickname:
        raise HTTPException(status_code=400, detail="Nickname already in use")

    new_user = User(
        email=user.email,
        nickname=user.nickname,
        password=hash_password(user.password),
        is_email_verified=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
