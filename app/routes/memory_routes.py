from pathlib import Path
from typing import Any, cast
import uuid
from datetime import datetime, timezone
import mimetypes

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.settings import settings
from app.database.deps import get_db
from app.models.memory import Memory
from app.models.memory_like import MemoryLike
from app.models.user import User
from app.security.auth import get_current_user

router = APIRouter()

UPLOAD_FOLDER = Path(settings.upload_dir)
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024

CONTENT_TYPE_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}

# Some devices/providers return these for valid image files.
ALLOWED_IMAGE_EXTENSIONS.update({".heif", ".jfif"})

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def _serialize_memory(item: Memory, author_nickname: str, like_count: int, liked_by_me: bool) -> dict[str, Any]:
    return {
        "id": int(cast(Any, item.id)),
        "description": str(cast(Any, item.description)),
        "image": str(cast(Any, item.image_path)),
        "user_id": int(cast(Any, item.user_id)),
        "author_nickname": author_nickname,
        "occurred_at": cast(Any, item.occurred_at).isoformat(),
        "like_count": like_count,
        "liked_by_me": liked_by_me,
    }

@router.post("/memories")
async def create_memory(
    description: str = Form(...),
    occurred_at: str | None = Form(None),
    images: list[UploadFile] = File(...),
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

    if not images:
        raise HTTPException(status_code=400, detail="Debes enviar al menos una imagen")

    if len(images) > 10:
        raise HTTPException(status_code=400, detail="Solo puedes subir hasta 10 imagenes por envio")

    parsed_occurred_at = datetime.utcnow()
    if occurred_at:
        try:
            parsed_occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            if parsed_occurred_at.tzinfo is not None:
                parsed_occurred_at = parsed_occurred_at.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Fecha de recuerdo invalida") from exc

    created_memories: list[Memory] = []
    for image in images:
        suffix = Path(image.filename or "").suffix.lower()
        if not suffix and image.content_type:
            suffix = CONTENT_TYPE_EXTENSION_MAP.get(image.content_type.lower(), "")

        if not suffix and image.content_type:
            guessed = mimetypes.guess_extension(image.content_type.lower()) or ""
            suffix = guessed.lower()

        normalized_content_type = (image.content_type or "").lower()
        # Allow generic octet-stream when extension is valid (common on some clients).
        content_type_ok = (
            not normalized_content_type
            or normalized_content_type.startswith("image/")
            or normalized_content_type == "application/octet-stream"
        )

        if not content_type_ok:
            raise HTTPException(status_code=400, detail="Solo se permiten imagenes")

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

        memory = Memory(
            description=description,
            image_path=image_path,
            user_id=current_user.id,
            couple_id=current_user.couple_id,
            occurred_at=parsed_occurred_at,
        )
        db.add(memory)
        created_memories.append(memory)

    db.commit()
    for memory in created_memories:
        db.refresh(memory)

    author_nickname = str(cast(Any, current_user.nickname or "usuario"))
    return {
        "created": [
            _serialize_memory(memory, author_nickname, 0, False)
            for memory in created_memories
        ]
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

    if not memories:
        return []

    memory_ids = [int(cast(Any, item.id)) for item in memories]
    author_ids = {int(cast(Any, item.user_id)) for item in memories}

    authors = (
        db.query(User.id, User.nickname)
        .filter(User.id.in_(author_ids))
        .all()
    )
    nickname_by_user = {
        int(cast(Any, user_id)): str(cast(Any, nickname or "usuario"))
        for user_id, nickname in authors
    }

    like_counts = (
        db.query(MemoryLike.memory_id, func.count(MemoryLike.id))
        .filter(MemoryLike.memory_id.in_(memory_ids))
        .group_by(MemoryLike.memory_id)
        .all()
    )
    like_count_by_memory = {
        int(cast(Any, memory_id)): int(cast(Any, count_value))
        for memory_id, count_value in like_counts
    }

    my_user_id = int(cast(Any, current_user.id))
    my_likes = (
        db.query(MemoryLike.memory_id)
        .filter(MemoryLike.memory_id.in_(memory_ids), MemoryLike.user_id == my_user_id)
        .all()
    )
    liked_by_me_ids = {int(cast(Any, memory_id)) for (memory_id,) in my_likes}

    return [
        _serialize_memory(
            item,
            nickname_by_user.get(int(cast(Any, item.user_id)), "usuario"),
            like_count_by_memory.get(int(cast(Any, item.id)), 0),
            int(cast(Any, item.id)) in liked_by_me_ids,
        )
        for item in memories
    ]


@router.post("/memories/{memory_id}/like")
def toggle_memory_like(
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Recuerdo no encontrado")

    if cast(Any, memory.couple_id) != cast(Any, current_user.couple_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a este recuerdo")

    user_id = int(cast(Any, current_user.id))
    existing_like = (
        db.query(MemoryLike)
        .filter(MemoryLike.memory_id == memory_id, MemoryLike.user_id == user_id)
        .first()
    )

    liked = False
    if existing_like:
        db.delete(existing_like)
    else:
        db.add(MemoryLike(memory_id=memory_id, user_id=user_id))
        liked = True

    db.commit()

    like_count = (
        db.query(func.count(MemoryLike.id))
        .filter(MemoryLike.memory_id == memory_id)
        .scalar()
    )
    return {
        "liked_by_me": liked,
        "like_count": int(cast(Any, like_count or 0)),
    }


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
