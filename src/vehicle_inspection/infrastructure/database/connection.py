"""Database connection management."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator


class DatabaseManager:
    """Database connection manager."""

    def __init__(self, database_url: str):
        """Initialize database manager."""
        # Convert postgresql:// to postgresql+asyncpg:// for async support
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self._engine: AsyncEngine | None = None
        self._database_url = database_url
        self._session_factory: sessionmaker | None = None

    async def connect(self) -> None:
        """Connect to database."""
        self._engine = create_async_engine(
            self._database_url,
            echo=True,  # Set to False in production
            pool_pre_ping=True,
        )

        self._session_factory = sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def disconnect(self) -> None:
        """Disconnect from database."""
        if self._engine:
            await self._engine.dispose()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        if not self._session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @property
    def engine(self) -> AsyncEngine:
        """Get database engine."""
        if not self._engine:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._engine
