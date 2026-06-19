from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class MessageCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None  # set this to reply in a thread


class MessageUpdate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    content: str
    channel_id: int
    user_id: int
    is_edited: bool
    parent_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PaginatedMessages(BaseModel):
    """Wraps a list of messages with pagination info."""
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
