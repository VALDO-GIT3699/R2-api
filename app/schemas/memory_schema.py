from pydantic import BaseModel


class MemoryResponse(BaseModel):
    id: int
    description: str
    image: str
