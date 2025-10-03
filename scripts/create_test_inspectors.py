"""Script to create test inspectors for development."""

import asyncio
import sys
from uuid import UUID
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.vehicle_inspection.infrastructure.database.models import InspectorModel
from src.vehicle_inspection.domain.entities.inspector import InspectorRole, InspectorStatus
from src.vehicle_inspection.domain.value_objects.auth import PasswordHasher


async def create_test_inspectors():
    """Create test inspectors for development."""
    # Database connection
    database_url = "postgresql+asyncpg://postgres:password@db:5432/vehicle_inspection"
    engine = create_async_engine(database_url, echo=True)

    try:
        # Create session factory
        async_session = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with async_session() as session:
            # Test inspector data
            test_inspectors = [
                {
                    "id": UUID("11111111-1111-1111-1111-111111111111"),
                    "email": "inspector@example.com",
                    "first_name": "John",
                    "last_name": "Inspector",
                    "phone": "+1234567890",
                    "role": InspectorRole.SENIOR,
                    "license_number": "INS001",
                    "status": InspectorStatus.ACTIVE,
                    "password": "inspector123"  # This will be hashed
                },
                {
                    "id": UUID("22222222-2222-2222-2222-222222222222"),
                    "email": "supervisor@example.com",
                    "first_name": "Jane",
                    "last_name": "Supervisor",
                    "phone": "+1234567891",
                    "role": InspectorRole.SUPERVISOR,
                    "license_number": "SUP001",
                    "status": InspectorStatus.ACTIVE,
                    "password": "supervisor123"  # This will be hashed
                },
                {
                    "id": UUID("33333333-3333-3333-3333-333333333333"),
                    "email": "junior@example.com",
                    "first_name": "Bob",
                    "last_name": "Junior",
                    "phone": "+1234567892",
                    "role": InspectorRole.JUNIOR,
                    "license_number": "JUN001",
                    "status": InspectorStatus.ACTIVE,
                    "password": "junior123"  # This will be hashed
                }
            ]

            for inspector_data in test_inspectors:
                # Check if inspector already exists
                existing_inspector = await session.get(InspectorModel, inspector_data["id"])

                if not existing_inspector:
                    # Hash password
                    password_hash = PasswordHasher.create_password_hash(inspector_data["password"])

                    # Create inspector
                    inspector = InspectorModel(
                        id=inspector_data["id"],
                        email=inspector_data["email"],
                        first_name=inspector_data["first_name"],
                        last_name=inspector_data["last_name"],
                        phone=inspector_data["phone"],
                        role=inspector_data["role"],
                        license_number=inspector_data["license_number"],
                        status=inspector_data["status"],
                        hire_date=datetime.utcnow(),
                        password_hash=password_hash,
                        failed_login_attempts=0,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )

                    session.add(inspector)
                    print(f"✅ Created inspector: {inspector_data['email']} ({inspector_data['role'].value})")
                else:
                    print(f"ℹ️ Inspector already exists: {inspector_data['email']}")

            await session.commit()
            print("✅ Test inspectors setup completed!")

    except Exception as e:
        print(f"❌ Error creating test inspectors: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_inspectors())
