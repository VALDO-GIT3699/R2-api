from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.user_schema import UserCreate, UserResponse
from app.models.user import User
from app.database.deps import get_db
from app.security.auth import hash_password

router = APIRouter()

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        password=hash_password(user.password),
        is_email_verified=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
