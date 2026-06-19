from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class MessageCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None  # set this to reply in a thread


class MessageUpdate(BaseModel):
    content: str


class AttachmentInfo(BaseModel):
    """File attached to a message — what the frontend needs to display it."""
    id: int
    filename: str
    url: str            # where to download/view it, e.g. /uploads/abc.png
    content_type: str
    size: int


class MessageResponse(BaseModel):
    id: int
    content: str
    channel_id: int
    user_id: int
    display_name: Optional[str] = None   # author's name, joined from users table
    username: Optional[str] = None
    is_edited: bool
    parent_id: Optional[int]
    attachment: Optional[AttachmentInfo] = None
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
