from pydantic import BaseModel, Field

from app.models import MessageStatus


class MessageIn(BaseModel):
    source: str = Field(min_length=1, max_length=32)
    external_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: int
    status: MessageStatus
    codes: list[str]
