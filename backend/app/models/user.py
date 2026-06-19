from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class User(Base):
    """
    Every person who signs up gets a row in this table.
    We NEVER store plain-text passwords — only a bcrypt hash.
    """
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    email        = Column(String(255), unique=True, index=True, nullable=False)
    username     = Column(String(50),  unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar_url   = Column(String(500), nullable=True)
    is_online    = Column(Boolean, default=False)
    is_active    = Column(Boolean, default=True)   # False = banned/deleted account
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())
