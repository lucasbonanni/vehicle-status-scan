"""Simple Pydantic schemas for booking API requests and responses."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from enum import Enum


class BookingStatusEnum(str, Enum):
    """Booking status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LicensePlateRequest(BaseModel):
    """Request model for license plate operations."""
    license_plate: str


class BookingRequest(BaseModel):
    """Request model for creating a booking."""
    license_plate: str
    appointment_date: datetime
    user_id: UUID


class BookingResponse(BaseModel):
    """Response model for booking operations."""
    id: UUID
    license_plate: str
    appointment_date: datetime
    user_id: UUID
    status: BookingStatusEnum
    created_at: datetime
    updated_at: datetime


class TimeSlotResponse(BaseModel):
    """Response model for time slot information."""
    date: datetime
    start_time: str
    end_time: str
    is_available: bool
    available_spots: int
    time_range: str


class AvailableSlotsRequest(BaseModel):
    """Request model for getting available slots."""
    date: str  # Date in YYYY-MM-DD format


class AvailableSlotsResponse(BaseModel):
    """Response model for available slots."""
    date: str
    available_slots: List[TimeSlotResponse]
    total_slots: int
    available_count: int


class BookingConfirmationRequest(BaseModel):
    """Request model for confirming a booking."""
    user_id: UUID


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
