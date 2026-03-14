from datetime import datetime

from pydantic import BaseModel, Field


class CoupleNoteCreateRequest(BaseModel):
    content: str = Field(min_length=2, max_length=500)


class CoupleNoteResponse(BaseModel):
    id: int
    couple_id: int
    author_user_id: int
    author_nickname: str
    content: str
    created_at: datetime
    like_count: int = 0
    liked_by_me: bool = False
