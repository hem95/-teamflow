from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class StartDMRequest(BaseModel):
    """Begin a DM with someone by their username."""
    username: str


class DMUser(BaseModel):
    """The other person in a conversation."""
    id: int
    username: str
    display_name: str
    is_online: bool

    model_config = {"from_attributes": True}


class DMConversationResponse(BaseModel):
    """A conversation in the sidebar — shows who you're talking to."""
    id: int
    other_user: DMUser
    created_at: datetime


class DirectMessageCreate(BaseModel):
    content: str


class DirectMessageResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    display_name: Optional[str] = None
    username: Optional[str] = None
    content: str
    is_edited: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PaginatedDirectMessages(BaseModel):
    messages: List[DirectMessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
