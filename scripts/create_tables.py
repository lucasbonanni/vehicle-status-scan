"""Script to initialize database tables."""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

from src.vehicle_inspection.infrastructure.database.models import Base


async def create_tables():
    """Create all database tables."""
    # Get database URL from environment or use default
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/vehicle_inspection"
    )

    # Create async engine
    engine = create_async_engine(database_url, echo=True)

    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Database tables created successfully!")

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
