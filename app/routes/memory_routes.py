from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
import shutil

from app.database.deps import get_db
from app.models.memory import Memory

router = APIRouter()

UPLOAD_FOLDER = "uploads"

@router.post("/memories")
def create_memory(
    description: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    file_location = f"{UPLOAD_FOLDER}/{image.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    memory = Memory(
        description=description,
        image_path=file_location,
        user_id=1
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return memory


@router.get("/memories")
def get_memories(db: Session = Depends(get_db)):

    memories = db.query(Memory).all()

    return memories
