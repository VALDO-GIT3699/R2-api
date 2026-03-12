from sqlalchemy import Column, Integer, String, ForeignKey
from app.database.database import Base

class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)
    image_path = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
