from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class DMConversation(Base):
    """
    A private conversation between users (currently 1-to-1).
    Think of it as a 'channel' that only its two participants can see.
    """
    __tablename__ = "dm_conversations"

    id         = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    participants = relationship("DMParticipant", back_populates="conversation", lazy="selectin")


class DMParticipant(Base):
    """
    Join table — links users to a conversation.
    For a 1-to-1 DM there are exactly two rows: one per person.
    """
    __tablename__ = "dm_participants"

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("dm_conversations.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)

    conversation = relationship("DMConversation", back_populates="participants")


class DirectMessage(Base):
    """A single message inside a DM conversation."""
    __tablename__ = "direct_messages"

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("dm_conversations.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    content         = Column(String(4000), nullable=False)
    is_edited       = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
