"""Script to initialize database tables and seed with test data."""

import asyncio
import os
import sys
from uuid import UUID
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.vehicle_inspection.infrastructure.database.models import Base, UserModel


async def setup_database():
    """Set up database tables and seed with test data."""
    # Get database URL from environment or use default
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@db:5432/vehicle_inspection"
    )

    # Convert to async format
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Create async engine
    engine = create_async_engine(database_url, echo=True)

    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Database tables created successfully!")

        # Create session factory
        async_session = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Seed test data
        async with async_session() as session:
            # Create test user
            test_user_id = UUID("550e8400-e29b-41d4-a716-446655440000")

            # Check if test user already exists
            existing_user = await session.get(UserModel, test_user_id)

            if not existing_user:
                test_user = UserModel(
                    id=test_user_id,
                    email="test@example.com",
                    first_name="Test",
                    last_name="User",
                    phone="+1234567890",
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(test_user)
                await session.commit()
                print("✅ Test user created successfully!")
            else:
                print("ℹ️ Test user already exists")

    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(setup_database())
