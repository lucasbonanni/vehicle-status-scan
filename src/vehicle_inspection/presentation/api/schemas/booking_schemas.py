"""Pydantic schemas for booking API requests and responses."""

from datetime import datetime, date as Date
from typing import List, Optional
from uuid import UUID
from enum import Enum

try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    # Handle the case where pydantic might not be available during type checking
    BaseModel = object
    Field = lambda *args, **kwargs: None
    validator = lambda *args, **kwargs: lambda f: f


class BookingStatus(Enum):
    """Booking status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LicensePlateRequest(BaseModel):
    """Request model for license plate operations."""
    license_plate: str = Field(..., min_length=3, max_length=10, description="Vehicle license plate")

    @validator('license_plate')
    def validate_license_plate(cls, v):
        """Validate license plate format."""
        if not v or not v.strip():
            raise ValueError('License plate cannot be empty')
        return v.strip().upper()


class BookingRequest(BaseModel):
    """Request model for creating a booking."""
    license_plate: str = Field(..., min_length=3, max_length=10, description="Vehicle license plate")
    appointment_date: datetime = Field(..., description="Desired appointment date and time")
    user_id: UUID = Field(..., description="ID of the user making the booking")

    @validator('license_plate')
    def validate_license_plate(cls, v):
        """Validate license plate format."""
        if not v or not v.strip():
            raise ValueError('License plate cannot be empty')
        return v.strip().upper()

    @validator('appointment_date')
    def validate_appointment_date(cls, v):
        """Validate appointment date is in the future."""
        if v <= datetime.utcnow():
            raise ValueError('Appointment must be scheduled for a future date')
        return v


class BookingResponse(BaseModel):
    """Response model for booking operations."""
    id: UUID
    license_plate: str
    appointment_date: datetime
    user_id: UUID
    status: BookingStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True


class TimeSlotResponse(BaseModel):
    """Response model for time slot information."""
    date: datetime
    start_time: str = Field(..., description="Start time in HH:MM format")
    end_time: str = Field(..., description="End time in HH:MM format")
    is_available: bool
    available_spots: int
    time_range: str = Field(..., description="Formatted time range")

    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        """Validate time format."""
        if not v or len(v) != 5 or v[2] != ':':
            raise ValueError('Time must be in HH:MM format')
        return v


class AvailableSlotsRequest(BaseModel):
    """Request model for getting available slots."""
    date: date = Field(..., description="Date to check for available slots")

    @validator('date')
    def validate_date(cls, v):
        """Validate date is not in the past."""
        if v < date.today():
            raise ValueError('Cannot check availability for past dates')
        return v


class AvailableSlotsResponse(BaseModel):
    """Response model for available slots."""
    date: date
    available_slots: List[TimeSlotResponse]
    total_slots: int
    available_count: int


class BookingConfirmationRequest(BaseModel):
    """Request model for confirming a booking."""
    user_id: UUID = Field(..., description="ID of the user confirming the booking")


class BookingListResponse(BaseModel):
    """Response model for listing bookings."""
    bookings: List[BookingResponse]
    total_count: int


class BookingActionResponse(BaseModel):
    """Response model for booking actions (confirm, cancel)."""
    success: bool
    message: str
    booking: Optional[BookingResponse] = None


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str
    message: str
    details: Optional[dict] = None
