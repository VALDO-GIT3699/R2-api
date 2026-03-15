from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.database.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)
    image_path = Column(String)
    image_deleted_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=True, index=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
