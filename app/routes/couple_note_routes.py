from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.models.couple_note import CoupleNote
from app.models.user import User
from app.schemas.couple_note_schema import CoupleNoteCreateRequest, CoupleNoteResponse
from app.security.auth import get_current_user

router = APIRouter()


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

    return CoupleNoteResponse(
        id=int(cast(Any, note.id)),
        couple_id=int(cast(Any, note.couple_id)),
        author_user_id=int(cast(Any, note.author_user_id)),
        content=str(cast(Any, note.content)),
        created_at=cast(datetime, cast(Any, note.created_at)),
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

    return [
        CoupleNoteResponse(
            id=int(cast(Any, item.id)),
            couple_id=int(cast(Any, item.couple_id)),
            author_user_id=int(cast(Any, item.author_user_id)),
            content=str(cast(Any, item.content)),
            created_at=cast(datetime, cast(Any, item.created_at)),
        )
        for item in notes
    ]
