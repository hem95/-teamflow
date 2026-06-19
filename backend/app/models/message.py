from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class Message(Base):
    """
    Every chat message is a row here.
    parent_id supports threaded replies (like Slack threads).
    """
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    content    = Column(String(4000), nullable=False)
    is_edited  = Column(Boolean, default=False)
    parent_id  = Column(Integer, ForeignKey("messages.id"), nullable=True)  # None = top-level message
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    channel = relationship("Channel", back_populates="messages")
    # Self-referencing: a message can have many replies, and a reply has one parent
    replies = relationship("Message", back_populates="parent")
    parent  = relationship("Message", back_populates="replies", remote_side=[id])
