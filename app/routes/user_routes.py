from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Any, cast

from app.schemas.user_schema import UserCreate, UserResponse
from app.models.user import User
from app.models.memory import Memory
from app.models.couple_note import CoupleNote
from app.models.appointment import Appointment
from app.models.memory_like import MemoryLike
from app.models.couple_note_like import CoupleNoteLike
from app.database.deps import get_db
from app.security.auth import hash_password
from app.security.auth import get_current_user

router = APIRouter()

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == user.email.lower(), User.deleted_at.is_(None))
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_nickname = (
        db.query(User)
        .filter(User.nickname == user.nickname, User.deleted_at.is_(None))
        .first()
    )
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


@router.delete("/users/me")
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()
    user_id = int(cast(Any, current_user.id))
    email_alias = f"eliminado_{user_id}_{int(now.timestamp())}@recuer2.local"
    nickname_alias = f"eliminado_{user_id}"[:24]

    db.query(Memory).filter(
        Memory.user_id == user_id,
        Memory.deleted_at.is_(None),
    ).update({Memory.deleted_at: now}, synchronize_session=False)

    db.query(CoupleNote).filter(
        CoupleNote.author_user_id == user_id,
        CoupleNote.deleted_at.is_(None),
    ).update({CoupleNote.deleted_at: now}, synchronize_session=False)

    db.query(Appointment).filter(
        Appointment.creator_user_id == user_id,
        Appointment.deleted_at.is_(None),
    ).update({Appointment.deleted_at: now}, synchronize_session=False)

    db.query(MemoryLike).filter(MemoryLike.user_id == user_id).delete(synchronize_session=False)
    db.query(CoupleNoteLike).filter(CoupleNoteLike.user_id == user_id).delete(synchronize_session=False)

    setattr(current_user, "deleted_at", now)
    setattr(current_user, "email", email_alias)
    setattr(current_user, "nickname", nickname_alias)
    setattr(current_user, "apple_sub", None)
    setattr(current_user, "couple_id", None)

    db.commit()
    return {"ok": True, "message": "Cuenta eliminada"}
