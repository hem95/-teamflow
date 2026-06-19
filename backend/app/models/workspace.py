import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base


class MemberRole(str, enum.Enum):
    owner  = "owner"   # created the workspace, has all permissions
    admin  = "admin"   # can manage channels and members
    member = "member"  # regular user


class Workspace(Base):
    """
    A Workspace is like a 'company' in Slack — it has its own channels
    and members. One user can belong to many workspaces.
    """
    __tablename__ = "workspaces"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)
    slug        = Column(String(50), unique=True, index=True, nullable=False)  # URL-safe name e.g. "my-team"
    description = Column(String(500), nullable=True)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    channels = relationship("Channel", back_populates="workspace", lazy="selectin")
    members  = relationship("WorkspaceMember", back_populates="workspace", lazy="selectin")


class WorkspaceMember(Base):
    """Join table — links users to workspaces with a role."""
    __tablename__ = "workspace_members"

    id           = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    role         = Column(Enum(MemberRole), default=MemberRole.member)
    joined_at    = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", back_populates="members")
