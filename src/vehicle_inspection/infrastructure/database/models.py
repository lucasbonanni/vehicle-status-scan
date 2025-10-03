"""SQLAlchemy database models."""

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from src.vehicle_inspection.domain.entities.booking import BookingStatus
from src.vehicle_inspection.domain.entities.inspector import InspectorRole, InspectorStatus

Base = declarative_base()


class BookingModel(Base):
    """SQLAlchemy model for bookings."""

    __tablename__ = "bookings"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Booking details
    license_plate = Column(String(20), nullable=False, index=True)
    appointment_date = Column(DateTime, nullable=False, index=True)
    status = Column(SQLEnum(BookingStatus), nullable=False, default=BookingStatus.PENDING)

    # User information
    user_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional booking information
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<BookingModel(id={self.id}, license_plate='{self.license_plate}', status='{self.status}')>"


class TimeSlotModel(Base):
    """SQLAlchemy model for time slots."""

    __tablename__ = "time_slots"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Time slot details
    date = Column(DateTime, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # Availability
    is_available = Column(Boolean, nullable=False, default=True)
    max_bookings = Column(Integer, nullable=False, default=1)
    current_bookings = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TimeSlotModel(id={self.id}, date={self.date}, available={self.is_available})>"


class VehicleModel(Base):
    """SQLAlchemy model for vehicles."""

    __tablename__ = "vehicles"

    # Primary key
    license_plate = Column(String(20), primary_key=True)

    # Vehicle details
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    vehicle_type = Column(String(20), nullable=False)  # 'car', 'motorcycle', etc.

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<VehicleModel(license_plate='{self.license_plate}', make='{self.make}', model='{self.model}')>"


class UserModel(Base):
    """SQLAlchemy model for users."""

    __tablename__ = "users"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # User details
    email = Column(String(255), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email='{self.email}', name='{self.first_name} {self.last_name}')>"


class InspectorModel(Base):
    """SQLAlchemy model for inspectors."""

    __tablename__ = "inspectors"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Inspector details
    email = Column(String(255), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)

    # Inspector-specific fields
    role = Column(SQLEnum(InspectorRole, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=InspectorRole.JUNIOR)
    license_number = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(SQLEnum(InspectorStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=InspectorStatus.ACTIVE)
    hire_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Authentication fields
    password_hash = Column(String(255), nullable=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<InspectorModel(id={self.id}, email='{self.email}', name='{self.first_name} {self.last_name}', role='{self.role}')>"
