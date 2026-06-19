from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# The engine is the actual connection to PostgreSQL
# echo=True prints every SQL query to the console (useful for debugging)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,           # keep 20 connections ready (handles many users at once)
    max_overflow=40,        # allow 40 extra connections during traffic spikes
)

# A "session" is like a shopping cart — you collect database actions,
# then commit them all at once (or roll back if something goes wrong)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# All database models (tables) inherit from this Base class
class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency — gives each request its own database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session           # hand the session to the route handler
            await session.commit()  # save all changes if no error
        except Exception:
            await session.rollback()  # undo all changes if there was an error
            raise
