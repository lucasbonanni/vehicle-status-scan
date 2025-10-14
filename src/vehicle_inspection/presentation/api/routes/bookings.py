"""Booking endpoints with database integration."""

from datetime import datetime, date as Date
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from src.vehicle_inspection.infrastructure.services import get_service_factory

router = APIRouter()


class BookingRequest(BaseModel):
    """Request to create a booking for vehicle inspection."""
    license_plate: str
    appointment_date: datetime
    # Note: user_id is handled internally, no user account required


class BookingResponse(BaseModel):
    """Booking response."""
    id: UUID
    license_plate: str
    appointment_date: datetime
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class TimeSlotResponse(BaseModel):
    """Time slot response."""
    date: datetime
    start_time: str
    end_time: str
    is_available: bool
    available_spots: int
    time_range: str


class AvailableSlotsResponse(BaseModel):
    """Available slots response."""
    date: str
    available_slots: List[TimeSlotResponse]
    total_slots: int
    available_count: int


class BookingActionRequest(BaseModel):
    """Request for booking actions (license plate-based, no user account required)."""
    pass  # No fields needed - booking actions work on booking ID only


# Default user ID for license plate-based bookings (no user accounts required)
DEFAULT_USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


@router.get("/available-slots")
async def get_available_slots(
    date: str = Query(..., description="Date in YYYY-MM-DD format")
) -> AvailableSlotsResponse:
    """Get available appointment slots for a specific date."""
    try:
        # Parse date
        target_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Check if date is not in the past
        if target_date < Date.today():
            raise HTTPException(status_code=400, detail="Cannot check availability for past dates")

        # Get available slots using database service
        service_factory = get_service_factory()
        async with service_factory.get_booking_service() as booking_service:
            slots = await booking_service.get_available_slots(target_date)

        # Convert to response format
        slot_responses = []
        for slot in slots:
            slot_response = TimeSlotResponse(
                date=slot.date,
                start_time=slot.start_time.strftime("%H:%M"),
                end_time=slot.end_time.strftime("%H:%M"),
                is_available=slot.is_available,
                available_spots=slot.available_spots,
                time_range=slot.time_range
            )
            slot_responses.append(slot_response)

        available_count = sum(1 for slot in slot_responses if slot.is_available)

        return AvailableSlotsResponse(
            date=date,
            available_slots=slot_responses,
            total_slots=len(slot_responses),
            available_count=available_count
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting available slots: {str(e)}") from e


@router.post("/")
async def create_booking(request: BookingRequest) -> BookingResponse:
    """Create a new vehicle inspection appointment using license plate."""
    try:
        # Use default user ID for license plate-based booking (no user account required)
        user_id = DEFAULT_USER_ID

        # Normalize datetime to UTC and remove timezone info for database compatibility
        appointment_date = request.appointment_date
        if appointment_date.tzinfo is not None:
            # Convert to UTC and make timezone-naive for database storage
            appointment_date = appointment_date.utctimetuple()
            appointment_date = datetime(*appointment_date[:6])

        # Create booking using database service
        service_factory = get_service_factory()
        async with service_factory.get_booking_service() as booking_service:
            booking = await booking_service.request_appointment(
                license_plate=request.license_plate,
                appointment_date=appointment_date,
                user_id=user_id
            )

        return BookingResponse(
            id=booking.id,
            license_plate=booking.license_plate,
            appointment_date=booking.appointment_date,
            user_id=booking.user_id,
            status=booking.status.value,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating booking: {str(e)}") from e


@router.get("/{booking_id}")
async def get_booking(
    booking_id: UUID = Path(..., description="Booking ID")
) -> BookingResponse:
    """Get booking by ID."""
    try:
        service_factory = get_service_factory()
        async with service_factory.get_booking_service() as booking_service:
            booking = await booking_service.get_booking(booking_id)

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        return BookingResponse(
            id=booking.id,
            license_plate=booking.license_plate,
            appointment_date=booking.appointment_date,
            user_id=booking.user_id,
            status=booking.status.value,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting booking: {str(e)}") from e


@router.post("/{booking_id}/confirm")
async def confirm_booking(
    booking_id: UUID = Path(..., description="Booking ID"),
    request: BookingActionRequest = BookingActionRequest()
) -> BookingResponse:
    """Confirm a booking."""
    try:
        user_id = DEFAULT_USER_ID

        service_factory = get_service_factory()
        async with service_factory.get_booking_service() as booking_service:
            booking = await booking_service.confirm_booking(booking_id, user_id)

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        return BookingResponse(
            id=booking.id,
            license_plate=booking.license_plate,
            appointment_date=booking.appointment_date,
            user_id=booking.user_id,
            status=booking.status.value,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming booking: {str(e)}") from e


@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: UUID = Path(..., description="Booking ID"),
    request: BookingActionRequest = BookingActionRequest()
) -> BookingResponse:
    """Cancel a booking."""
    try:
        user_id = DEFAULT_USER_ID

        service_factory = get_service_factory()
        async with service_factory.get_booking_service() as booking_service:
            booking = await booking_service.cancel_booking(booking_id, user_id)

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        return BookingResponse(
            id=booking.id,
            license_plate=booking.license_plate,
            appointment_date=booking.appointment_date,
            user_id=booking.user_id,
            status=booking.status.value,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling booking: {str(e)}") from e


@router.get("/vehicle/{license_plate}")
async def get_vehicle_bookings(
    license_plate: str = Path(..., description="Vehicle license plate (e.g., ABC123)")
) -> List[BookingResponse]:
    """Get all inspection bookings for a specific vehicle by license plate."""
    try:
        service_factory = get_service_factory()
        async with service_factory.get_booking_service() as booking_service:
            bookings = await booking_service.get_vehicle_bookings(license_plate)

        return [
            BookingResponse(
                id=booking.id,
                license_plate=booking.license_plate,
                appointment_date=booking.appointment_date,
                user_id=booking.user_id,
                status=booking.status.value,
                created_at=booking.created_at,
                updated_at=booking.updated_at
            )
            for booking in bookings
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting vehicle bookings: {str(e)}") from e
