"""Script to create default user for booking system."""

import asyncio
from uuid import UUID
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.sql import text

DEFAULT_USER_ID = "550e8400-e29b-41d4-a716-446655440000"

def create_default_user():
    """Create default user for booking system."""
    # Connect to database
    engine = create_engine("postgresql://postgres:password@db:5432/vehicle_inspection")

    with engine.connect() as conn:
        # Check if user already exists
        result = conn.execute(text(
            "SELECT COUNT(*) FROM users WHERE id = :user_id"
        ), {"user_id": DEFAULT_USER_ID})

        count = result.scalar()

        if count > 0:
            print("✅ Default user already exists")
            return

        # Insert default user
        conn.execute(text("""
            INSERT INTO users (
                id, email, first_name, last_name, phone, is_active, created_at, updated_at
            ) VALUES (
                :id, :email, :first_name, :last_name, :phone, :is_active, :created_at, :updated_at
            )
        """), {
            "id": DEFAULT_USER_ID,
            "email": "default@example.com",
            "first_name": "Default",
            "last_name": "User",
            "phone": "+1234567890",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        conn.commit()
        print("✅ Default user created successfully!")

if __name__ == "__main__":
    create_default_user()
