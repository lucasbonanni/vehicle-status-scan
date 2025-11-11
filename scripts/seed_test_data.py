#!/usr/bin/env python3
"""
Test data seeding script for Vehicle Inspection System.

This script generates realistic test data for demonstration and testing purposes.
It creates:
- Test inspector (with provided email/password)
- Test vehicles (cars and motorcycles)
- Sample inspections at various completion stages
- Test bookings

Run this script after database migration:
    python3 scripts/seed_test_data.py

Or set DATABASE_URL environment variable:
    DATABASE_URL=postgresql://user:password@localhost/db python3 scripts/seed_test_data.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.vehicle_inspection.infrastructure.database.models import (
    InspectorModel,
    VehicleModel,
    InspectionModel,
    UserModel,
)
from src.vehicle_inspection.domain.value_objects.auth import PasswordHasher
from src.vehicle_inspection.domain.entities.inspector import (
    InspectorRole,
    InspectorStatus,
)
from src.vehicle_inspection.domain.entities.inspection import InspectionStatus
from src.vehicle_inspection.domain.entities.vehicle import VehicleType


# Configuration
TEST_INSPECTOR_EMAIL = "test@example.com"
TEST_INSPECTOR_PASSWORD = "testpassword123"
TEST_INSPECTOR_LICENSE = "LIC-TEST-001"


def get_database_url() -> str:
    """Get database URL from environment or use default."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Please set it before running this script."
        )
    return db_url


def create_test_inspector(session: Session) -> InspectorModel:
    """Create test inspector with known credentials."""
    # Check if inspector already exists
    existing = (
        session.query(InspectorModel)
        .filter(InspectorModel.email == TEST_INSPECTOR_EMAIL)
        .first()
    )

    if existing:
        print(f"✓ Test inspector already exists: {existing.email}")
        return existing

    # Hash password
    password_hash = PasswordHasher.create_password_hash(TEST_INSPECTOR_PASSWORD)

    inspector = InspectorModel(
        id=uuid4(),
        email=TEST_INSPECTOR_EMAIL,
        first_name="Test",
        last_name="Inspector",
        phone="+1-555-0100",
        role=InspectorRole.SENIOR.value,
        license_number=TEST_INSPECTOR_LICENSE,
        status=InspectorStatus.ACTIVE.value,
        password_hash=password_hash,
        hire_date=datetime.now(timezone.utc) - timedelta(days=2),
    )

    session.add(inspector)
    session.commit()
    print(f"✓ Created test inspector: {inspector.email}")
    return inspector


def create_test_vehicles(session: Session) -> list[VehicleModel]:
    """Create test vehicles for inspection."""
    vehicles_data = [
        {
            "license_plate": "ABC1234",
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "vehicle_type": VehicleType.CAR.value,
        },
        {
            "license_plate": "XYZ9876",
            "make": "Honda",
            "model": "Civic",
            "year": 2021,
            "vehicle_type": VehicleType.CAR.value,
        },
        {
            "license_plate": "MCY5001",
            "make": "Harley-Davidson",
            "model": "Street 750",
            "year": 2019,
            "vehicle_type": VehicleType.MOTORCYCLE.value,
        },
        {
            "license_plate": "MKE2023",
            "make": "BMW",
            "model": "S1000RR",
            "year": 2023,
            "vehicle_type": VehicleType.MOTORCYCLE.value,
        },
    ]

    created_vehicles = []
    for vehicle_data in vehicles_data:
        # Check if vehicle already exists
        existing = (
            session.query(VehicleModel)
            .filter(VehicleModel.license_plate == vehicle_data["license_plate"])
            .first()
        )

        if existing:
            print(f"✓ Vehicle already exists: {existing.license_plate}")
            created_vehicles.append(existing)
            continue

        vehicle = VehicleModel(**vehicle_data)
        session.add(vehicle)
        created_vehicles.append(vehicle)

    session.commit()
    print(f"✓ Created/found {len(created_vehicles)} test vehicles")
    return created_vehicles


def create_test_inspections(session: Session, inspector: InspectorModel) -> None:
    """Create sample inspections at various stages."""
    vehicles = session.query(VehicleModel).all()

    if not vehicles:
        print("⚠ No vehicles found. Creating test vehicles first.")
        vehicles = create_test_vehicles(session)

    inspection_scenarios = [
        # Inspection 1: DRAFT status (no scores yet)
        {
            "license_plate": vehicles[0].license_plate,
            "vehicle_type": vehicles[0].vehicle_type,
            "status": InspectionStatus.DRAFT.value,
            "checkpoint_scores": None,
            "total_score": None,
            "is_safe": None,
            "observations": "Inspection in progress...",
        },
        # Inspection 2: COMPLETED with safe status (high score)
        {
            "license_plate": vehicles[1].license_plate,
            "vehicle_type": vehicles[1].vehicle_type,
            "status": InspectionStatus.COMPLETED.value,
            "checkpoint_scores": [
                {
                    "checkpoint_type": "braking_system",
                    "score": 9,
                    "notes": "Excellent condition",
                },
                {
                    "checkpoint_type": "steering_system",
                    "score": 8,
                    "notes": "Good alignment",
                },
                {
                    "checkpoint_type": "lighting_system",
                    "score": 10,
                    "notes": "All working",
                },
                {
                    "checkpoint_type": "body_structure",
                    "score": 9,
                    "notes": "Clean, no cracks",
                },
                {
                    "checkpoint_type": "electrical_system",
                    "score": 8,
                    "notes": "Running smoothly",
                },
                {
                    "checkpoint_type": "suspension_system",
                    "score": 9,
                    "notes": "Good alignment",
                },
                {
                    "checkpoint_type": "tires",
                    "score": 10,
                    "notes": "All functional",
                },
                {
                    "checkpoint_type": "gas_emissions",
                    "score": 9,
                    "notes": "Within limits",
                },
            ],
            "total_score": 72,
            "is_safe": True,
            "observations": "Vehicle passed inspection. Ready for road.",
        },
        # Inspection 3: COMPLETED but unsafe (low score)
        {
            "license_plate": vehicles[2].license_plate,
            "vehicle_type": vehicles[2].vehicle_type,
            "status": InspectionStatus.COMPLETED.value,
            "checkpoint_scores": [
                {
                    "checkpoint_type": "braking_system",
                    "score": 4,
                    "notes": "Worn pads detected",
                },
                {
                    "checkpoint_type": "steering_system",
                    "score": 3,
                    "notes": "Loose play",
                },
                {
                    "checkpoint_type": "lighting_system",
                    "score": 5,
                    "notes": "Rear lights not working",
                },
                {
                    "checkpoint_type": "body_structure",
                    "score": 4,
                    "notes": "Large chip in glass",
                },
                {
                    "checkpoint_type": "electrical_system",
                    "score": 3,
                    "notes": "Battery failing",
                },
                {
                    "checkpoint_type": "suspension_system",
                    "score": 4,
                    "notes": "Loose components",
                },
                {"checkpoint_type": "tires", "score": 3, "notes": "Low tread depth"},
                {
                    "checkpoint_type": "gas_emissions",
                    "score": 3,
                    "notes": "Exceeds limits",
                },
            ],
            "total_score": 31,
            "is_safe": False,
            "observations": "Vehicle FAILED inspection. Requires reinspection after repairs.",
            "requires_reinspection": True,
        },
        # Inspection 4: REINSPECTION (after repairs)
        {
            "license_plate": vehicles[3].license_plate,
            "vehicle_type": vehicles[3].vehicle_type,
            "status": InspectionStatus.COMPLETED.value,
            "checkpoint_scores": [
                {
                    "checkpoint_type": "braking_system",
                    "score": 9,
                    "notes": "New pads installed",
                },
                {
                    "checkpoint_type": "steering_system",
                    "score": 8,
                    "notes": "Alignment corrected",
                },
                {
                    "checkpoint_type": "lighting_system",
                    "score": 9,
                    "notes": "All lights repaired",
                },
                {
                    "checkpoint_type": "body_structure",
                    "score": 8,
                    "notes": "Chip sealed",
                },
                {
                    "checkpoint_type": "electrical_system",
                    "score": 8,
                    "notes": "Battery replaced",
                },
                {
                    "checkpoint_type": "suspension_system",
                    "score": 9,
                    "notes": "Tightened",
                },
                {
                    "checkpoint_type": "tires",
                    "score": 8,
                    "notes": "Replaced with new tires",
                },
                {
                    "checkpoint_type": "gas_emissions",
                    "score": 9,
                    "notes": "Emissions corrected",
                },
            ],
            "total_score": 70,
            "is_safe": True,
            "observations": "Vehicle PASSED reinspection after repairs. All safety issues resolved.",
        },
    ]

    for idx, scenario in enumerate(inspection_scenarios):
        # Check if similar inspection already exists
        existing = (
            session.query(InspectionModel)
            .filter(
                InspectionModel.license_plate == scenario["license_plate"],
                InspectionModel.status == scenario["status"],
            )
            .first()
        )

        if existing:
            print(f"✓ Inspection scenario {idx + 1} already exists")
            continue

        inspection = InspectionModel(
            id=uuid4(),
            license_plate=scenario["license_plate"],
            vehicle_type=scenario["vehicle_type"],
            inspector_id=inspector.id,
            status=scenario["status"],
            checkpoint_scores=scenario["checkpoint_scores"],
            total_score=scenario["total_score"],
            is_safe=scenario["is_safe"],
            requires_reinspection=scenario.get("requires_reinspection", False),
            observations=scenario["observations"],
            created_at=datetime.now(timezone.utc) - timedelta(days=idx),
            updated_at=datetime.now(timezone.utc) - timedelta(days=idx),
            completed_at=datetime.now(timezone.utc) - timedelta(days=idx)
            if scenario["status"] == InspectionStatus.COMPLETED.value
            else None,
        )

        session.add(inspection)

    session.commit()
    print(f"✓ Created {len(inspection_scenarios)} test inspection scenarios")


def create_test_users(session: Session) -> None:
    """Create test regular users for bookings."""
    users_data = [
        {
            "email": "user1@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1-555-0101",
        },
        {
            "email": "user2@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "+1-555-0102",
        },
    ]

    for user_data in users_data:
        existing = (
            session.query(UserModel)
            .filter(UserModel.email == user_data["email"])
            .first()
        )

        if existing:
            continue

        user = UserModel(id=uuid4(), **user_data)
        session.add(user)

    session.commit()
    print("✓ Created test users")


def seed_database() -> None:
    """Main function to seed the database with test data."""
    print("\n" + "=" * 60)
    print("Vehicle Inspection System - Test Data Seeding")
    print("=" * 60 + "\n")

    # Get database URL
    db_url = get_database_url()
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else 'local'}")

    # Create engine (convert async URL to sync for initialization)
    # Replace postgresql+asyncpg with postgresql for sync engine
    sync_db_url = db_url.replace("postgresql+asyncpg", "postgresql")

    engine = create_engine(sync_db_url, echo=False)

    # Create session
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()

    try:
        print("\n📋 Creating test data...\n")

        # Create test inspector
        inspector = create_test_inspector(session)

        # Create test vehicles
        create_test_vehicles(session)

        # Create test inspections
        create_test_inspections(session, inspector)

        # Create test users
        create_test_users(session)

        print("\n" + "=" * 60)
        print("✅ Test data seeding completed successfully!")
        print("=" * 60)
        print("\n📝 Test Inspector Credentials:")
        print(f"   Email:    {TEST_INSPECTOR_EMAIL}")
        print(f"   Password: {TEST_INSPECTOR_PASSWORD}")
        print("\n💡 Test Data Created:")
        print("   • 1 test inspector (SENIOR role)")
        print("   • 4 test vehicles (2 cars, 2 motorcycles)")
        print("   • 4 inspection scenarios (various statuses)")
        print("   • 2 test users (for bookings)")
        print("\n🔗 Next steps:")
        print("   1. Start the backend: docker-compose up -d backend")
        print("   2. Login with test credentials: /api/v1/auth/login")
        print("   3. Use returned JWT token in Authorization header")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error seeding database: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
