from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.deps import get_db
from app.models.couple_note import CoupleNote
from app.models.couple_note_like import CoupleNoteLike
from app.models.user import User
from app.schemas.couple_note_schema import CoupleNoteCreateRequest, CoupleNoteResponse
from app.security.auth import get_current_user

router = APIRouter()


def _serialize_note(
    item: CoupleNote,
    author_nickname: str,
    like_count: int,
    liked_by_me: bool,
) -> CoupleNoteResponse:
    return CoupleNoteResponse(
        id=int(cast(Any, item.id)),
        couple_id=int(cast(Any, item.couple_id)),
        author_user_id=int(cast(Any, item.author_user_id)),
        author_nickname=author_nickname,
        content=str(cast(Any, item.content)),
        created_at=cast(datetime, cast(Any, item.created_at)),
        like_count=like_count,
        liked_by_me=liked_by_me,
    )


def _require_partner(user: User) -> int:
    couple_id = cast(int | None, cast(Any, user.couple_id))
    if couple_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PAIR_REQUIRED",
                "message": "Debes vincularte con tu pareja para usar dedicatorias.",
            },
        )
    return couple_id


@router.post("/pair/notes", response_model=CoupleNoteResponse)
def create_couple_note(
    payload: CoupleNoteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    couple_id = _require_partner(current_user)

    note = CoupleNote(
        couple_id=couple_id,
        author_user_id=int(cast(Any, current_user.id)),
        content=payload.content.strip(),
        created_at=datetime.utcnow(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return _serialize_note(
        note,
        str(cast(Any, current_user.nickname or "usuario")),
        0,
        False,
    )


@router.get("/pair/notes", response_model=list[CoupleNoteResponse])
def get_couple_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    couple_id = _require_partner(current_user)

    notes = (
        db.query(CoupleNote)
        .filter(CoupleNote.couple_id == couple_id)
        .order_by(CoupleNote.created_at.desc())
        .all()
    )

    if not notes:
        return []

    note_ids = [int(cast(Any, item.id)) for item in notes]
    author_ids = {int(cast(Any, item.author_user_id)) for item in notes}
    authors = db.query(User.id, User.nickname).filter(User.id.in_(author_ids)).all()
    nickname_by_user = {
        int(cast(Any, user_id)): str(cast(Any, nickname or "usuario"))
        for user_id, nickname in authors
    }

    like_counts = (
        db.query(CoupleNoteLike.note_id, func.count(CoupleNoteLike.id))
        .filter(CoupleNoteLike.note_id.in_(note_ids))
        .group_by(CoupleNoteLike.note_id)
        .all()
    )
    like_count_by_note = {
        int(cast(Any, note_id)): int(cast(Any, count_value))
        for note_id, count_value in like_counts
    }

    current_user_id = int(cast(Any, current_user.id))
    my_likes = (
        db.query(CoupleNoteLike.note_id)
        .filter(CoupleNoteLike.note_id.in_(note_ids), CoupleNoteLike.user_id == current_user_id)
        .all()
    )
    liked_by_me_ids = {int(cast(Any, note_id)) for (note_id,) in my_likes}

    return [
        _serialize_note(
            item,
            nickname_by_user.get(int(cast(Any, item.author_user_id)), "usuario"),
            like_count_by_note.get(int(cast(Any, item.id)), 0),
            int(cast(Any, item.id)) in liked_by_me_ids,
        )
        for item in notes
    ]


@router.post("/pair/notes/{note_id}/like")
def toggle_couple_note_like(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(CoupleNote).filter(CoupleNote.id == note_id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Dedicatoria no encontrada")

    user_couple_id = cast(int | None, cast(Any, current_user.couple_id))
    note_couple_id = int(cast(Any, note.couple_id))
    if user_couple_id is None or note_couple_id != user_couple_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta dedicatoria")

    user_id = int(cast(Any, current_user.id))
    existing_like = (
        db.query(CoupleNoteLike)
        .filter(CoupleNoteLike.note_id == note_id, CoupleNoteLike.user_id == user_id)
        .first()
    )

    liked = False
    if existing_like:
        db.delete(existing_like)
    else:
        db.add(CoupleNoteLike(note_id=note_id, user_id=user_id))
        liked = True

    db.commit()

    like_count = (
        db.query(func.count(CoupleNoteLike.id))
        .filter(CoupleNoteLike.note_id == note_id)
        .scalar()
    )
    return {
        "liked_by_me": liked,
        "like_count": int(cast(Any, like_count or 0)),
    }
