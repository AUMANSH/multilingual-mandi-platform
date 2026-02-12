"""
Database configuration and session management.

This module sets up SQLAlchemy with async PostgreSQL support and provides
database session management for the application.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

from .config import get_database_url
from .models.base import Base


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: str, test_mode: bool = False):
        """Initialize database manager with connection URL."""
        self.database_url = database_url
        self.test_mode = test_mode
        
        # Create async engine
        engine_kwargs = {
            "echo": False,  # Set to True for SQL logging in development
            "future": True,
        }
        
        # Use NullPool for testing to avoid connection issues
        if test_mode:
            engine_kwargs["poolclass"] = NullPool
        
        self.engine = create_async_engine(database_url, **engine_kwargs)
        
        # Create session factory
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close the database engine."""
        await self.engine.dispose()


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_database_manager(test_mode: bool = False) -> DatabaseManager:
    """Get or create the global database manager."""
    global _db_manager
    
    if _db_manager is None or test_mode:
        database_url = get_database_url(test=test_mode)
        _db_manager = DatabaseManager(database_url, test_mode=test_mode)
    
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions in FastAPI."""
    db_manager = get_database_manager()
    async for session in db_manager.get_session():
        yield session


async def init_database():
    """Initialize database tables (for development/testing)."""
    db_manager = get_database_manager()
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database():
    """Close database connections."""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None