"""Script to initialize database tables for Docker setup."""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.vehicle_inspection.infrastructure.database.models import Base
from src.vehicle_inspection.domain.entities.inspector import InspectorRole, InspectorStatus
from src.vehicle_inspection.domain.value_objects.auth import PasswordHasher
from src.vehicle_inspection.infrastructure.database.models import InspectorModel
from uuid import UUID


def init_tables():
    """Initialize database tables."""
    # Use regular SQLAlchemy for initial setup
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@db:5432/vehicle_inspection"
    )

    engine = create_engine(database_url)

    # Drop existing tables (comment this out if you want to preserve data)
    Base.metadata.drop_all(engine)

    # Create all tables
    Base.metadata.create_all(engine)

    print("✅ Database tables created successfully!")

    # Create test user
    with engine.connect() as conn:
        # First check what values are allowed in the enum
        enum_values = conn.execute(text("SELECT enum_range(NULL::inspectorrole)")).scalar()
        enum_values_status = conn.execute(text("SELECT enum_range(NULL::inspectorstatus)")).scalar()
        print(f"Available role values: {enum_values}")
        print(f"Available status values: {enum_values_status}")

        inspector = {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567890",
            "role": "senior",  # Using lowercase as that's likely what's in the DB
            "license_number": "TEST001",
            "status": "active",  # Using lowercase as that's likely what's in the DB
            "password_hash": PasswordHasher.create_password_hash("testpassword123"),
            "created_at": "NOW()",
            "updated_at": "NOW()",
            "hire_date": "NOW()"
        }

        # Insert the inspector
        conn.execute(text("""
            INSERT INTO inspectors (
                id, email, first_name, last_name, phone, role, license_number, status,
                password_hash, created_at, updated_at, hire_date, failed_login_attempts
            )
            VALUES (
                :id, :email, :first_name, :last_name, :phone, :role, :license_number, :status,
                :password_hash, NOW(), NOW(), NOW(), 0
            )
        """), inspector)

        conn.commit()

    print("✅ Test user created successfully!")

if __name__ == "__main__":
    init_tables()
