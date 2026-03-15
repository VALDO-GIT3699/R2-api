from pydantic import BaseModel


class MemoryResponse(BaseModel):
    id: int
    description: str
    image: str


class MemoryCommentCreate(BaseModel):
    content: str


class MemoryCommentResponse(BaseModel):
    id: int
    memory_id: int
    user_id: int
    author_nickname: str
    content: str
    created_at: str
    can_delete: bool
