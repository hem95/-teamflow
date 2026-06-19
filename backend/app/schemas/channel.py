from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_private: bool = False

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        # Channel names are lowercase with hyphens, like Slack
        v = v.lower().replace(" ", "-")
        if len(v) < 1 or len(v) > 80:
            raise ValueError("Channel name must be 1-80 characters")
        return v


class ChannelResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_private: bool
    workspace_id: int
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}
