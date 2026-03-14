from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer

from app.database.database import Base


class MemoryLike(Base):
    __tablename__ = "memory_likes"

    id = Column(Integer, primary_key=True, index=True)
    memory_id = Column(Integer, ForeignKey("memories.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
