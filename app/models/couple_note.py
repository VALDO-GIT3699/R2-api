from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.database.database import Base


class CoupleNote(Base):
    __tablename__ = "couple_notes"

    id = Column(Integer, primary_key=True, index=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
