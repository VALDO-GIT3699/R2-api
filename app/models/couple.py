from datetime import datetime

from sqlalchemy import Column, DateTime, Integer

from app.database.database import Base


class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
