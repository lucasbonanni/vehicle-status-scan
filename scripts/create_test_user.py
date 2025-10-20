"""Script to create a test user for development."""

import asyncio
from uuid import UUID

from src.vehicle_inspection.domain.entities.inspector import InspectorRole, InspectorStatus
from src.vehicle_inspection.infrastructure.database.models import InspectorModel
from src.vehicle_inspection.domain.value_objects.auth import PasswordHasher
from src.vehicle_inspection.infrastructure.database.connection import DatabaseManager


async def create_test_user():
    """Create test user for development."""
    db_manager = DatabaseManager("postgresql://postgres:password@db:5432/vehicle_inspection")
    await db_manager.connect()

    async with db_manager.get_session() as session:
        inspector = InspectorModel(
            id=UUID('11111111-1111-1111-1111-111111111111'),
            email='test@example.com',
            first_name='Test',
            last_name='User',
            phone='+1234567890',
            role=InspectorRole.SENIOR,
            license_number='TEST001',
            status=InspectorStatus.ACTIVE,
            password_hash=PasswordHasher.hash_password('testpassword123')
        )
        session.add(inspector)
        await session.commit()

    await db_manager.disconnect()

if __name__ == '__main__':
    asyncio.run(create_test_user())
