from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class Channel(Base):
    """
    A Channel lives inside a Workspace (like #general or #engineering).
    Private channels are only visible to their members.
    """
    __tablename__ = "channels"

    id           = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name         = Column(String(80), nullable=False)
    description  = Column(String(300), nullable=True)
    is_private   = Column(Boolean, default=False)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", back_populates="channels")
    messages  = relationship("Message", back_populates="channel", lazy="dynamic")
    members   = relationship("ChannelMember", back_populates="channel", lazy="selectin")


class ChannelMember(Base):
    """Join table — tracks which users are in which channel."""
    __tablename__ = "channel_members"

    id         = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at  = Column(DateTime(timezone=True), server_default=func.now())

    channel = relationship("Channel", back_populates="members")
