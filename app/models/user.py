from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    apple_sub = Column(String, unique=True, nullable=True, index=True)
    is_email_verified = Column(Boolean, nullable=False, default=False)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=True, index=True)
