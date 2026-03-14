from pathlib import Path
from typing import Any, cast
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.database.deps import get_db
from app.models.memory import Memory
from app.models.user import User
from app.security.auth import get_current_user

router = APIRouter()

UPLOAD_FOLDER = Path(settings.upload_dir)
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

@router.post("/memories")
async def create_memory(
    description: str = Form(...),
    occurred_at: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.couple_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PAIR_REQUIRED",
                "message": "Debes vincularte con tu pareja antes de crear recuerdos.",
            },
        )

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten imagenes")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato de imagen no soportado")

    image_bytes = await image.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"La imagen excede {settings.max_upload_mb}MB",
        )

    file_name = f"{uuid.uuid4().hex}{suffix}"
    file_location = UPLOAD_FOLDER / file_name
    file_location.write_bytes(image_bytes)

    image_path = f"{settings.upload_dir}/{file_name}".replace("\\", "/")

    parsed_occurred_at = datetime.utcnow()
    if occurred_at:
        try:
            parsed_occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            if parsed_occurred_at.tzinfo is not None:
                parsed_occurred_at = parsed_occurred_at.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Fecha de recuerdo invalida") from exc

    memory = Memory(
        description=description,
        image_path=image_path,
        user_id=current_user.id,
        couple_id=current_user.couple_id,
        occurred_at=parsed_occurred_at,
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return {
        "id": int(cast(Any, memory.id)),
        "description": str(cast(Any, memory.description)),
        "image": str(cast(Any, memory.image_path)),
        "occurred_at": cast(Any, memory.occurred_at).isoformat(),
    }


@router.get("/memories")
def get_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.couple_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PAIR_REQUIRED",
                "message": "Debes vincularte con tu pareja antes de ver el feed.",
            },
        )

    memories = (
        db.query(Memory)
        .filter(Memory.couple_id == current_user.couple_id)
        .order_by(Memory.occurred_at.desc(), Memory.id.desc())
        .all()
    )

    return [
        {
            "id": int(cast(Any, item.id)),
            "description": str(cast(Any, item.description)),
            "image": str(cast(Any, item.image_path)),
            "occurred_at": cast(Any, item.occurred_at).isoformat(),
        }
        for item in memories
    ]


@router.get("/memories/reminders/monthly")
def monthly_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.couple_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PAIR_REQUIRED",
                "message": "Debes vincularte con tu pareja antes de ver recordatorios.",
            },
        )

    now = datetime.utcnow().date()

    couple_memories = (
        db.query(Memory)
        .filter(Memory.couple_id == current_user.couple_id)
        .all()
    )

    due_items = []
    for item in couple_memories:
        occurred_at = cast(Any, item.occurred_at)
        if occurred_at is None:
            continue

        occurred_date = occurred_at.date()
        if occurred_date > now:
            continue

        months_delta = (now.year - occurred_date.year) * 12 + (now.month - occurred_date.month)
        if months_delta < 1:
            continue

        if occurred_date.day != now.day:
            continue

        due_items.append(
            {
                "id": int(cast(Any, item.id)),
                "title": f"Hoy hace {months_delta} mes{'es' if months_delta > 1 else ''}...",
                "description": str(cast(Any, item.description)),
                "image": str(cast(Any, item.image_path)),
                "occurred_at": occurred_at.isoformat(),
            }
        )

    return due_items
