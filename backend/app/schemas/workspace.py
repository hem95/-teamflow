from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import re


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Workspace name must be 2-100 characters")
        return v


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
