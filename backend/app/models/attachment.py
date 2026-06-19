from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from app.database import Base


class Attachment(Base):
    """
    A file attached to a message.

    A row points at EITHER a channel message (message_id) OR a direct
    message (dm_message_id) — whichever the file was sent in.

    We store the original filename (to show the user) and a 'stored_name'
    (a random unique name on disk) separately. Never trust the original
    filename for the path on disk — that's how path-traversal attacks happen.
    """
    __tablename__ = "attachments"

    id            = Column(Integer, primary_key=True, index=True)
    message_id    = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    dm_message_id = Column(Integer, ForeignKey("direct_messages.id"), nullable=True, index=True)
    uploader_id   = Column(Integer, ForeignKey("users.id"), nullable=False)

    filename      = Column(String(255), nullable=False)   # original name, e.g. "report.pdf"
    stored_name   = Column(String(255), nullable=False)   # name on disk, e.g. "a1b2...e9.pdf"
    content_type  = Column(String(120), nullable=False)   # e.g. "image/png"
    size          = Column(Integer, nullable=False)       # bytes
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
