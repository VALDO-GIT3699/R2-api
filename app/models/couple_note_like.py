from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer

from app.database.database import Base


class CoupleNoteLike(Base):
    __tablename__ = "couple_note_likes"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("couple_notes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
