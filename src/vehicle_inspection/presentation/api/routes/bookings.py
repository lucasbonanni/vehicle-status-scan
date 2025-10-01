"""Booking endpoints."""

from datetime import datetime, date as Date
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from src.vehicle_inspection.infrastructure.repositories.simple_booking_service import InMemoryBookingService

router = APIRouter()

# Global service instance (In production, this would be injected)
booking_service = InMemoryBookingService()


class BookingRequest(BaseModel):
    """Request to create a booking."""
    license_plate: str
    appointment_date: datetime
    user_id: Optional[UUID] = None  # Optional for demo, will use test user


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
    """Request for booking actions."""
    user_id: Optional[UUID] = None


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

        # Get available slots
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
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting available slots: {str(e)}")


@router.post("/")
async def create_booking(request: BookingRequest) -> BookingResponse:
    """Create a new booking appointment."""
    try:
        # Use test user if no user_id provided
        user_id = request.user_id or booking_service.get_test_user_id()

        # Create booking
        booking = await booking_service.create_booking(
            license_plate=request.license_plate,
            appointment_date=request.appointment_date,
            user_id=user_id
        )

        return BookingResponse(
            id=booking.id,
            license_plate=booking.license_plate,
            appointment_date=booking.appointment_date,
            user_id=booking.user_id,
            status=booking.status,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating booking: {str(e)}")


@router.get("/{booking_id}")
async def get_booking(
    booking_id: UUID = Path(..., description="Booking ID")
) -> BookingResponse:
    """Get booking by ID."""
    try:
        booking = await booking_service.get_booking(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        return BookingResponse(
            id=booking.id,
            license_plate=booking.license_plate,
            appointment_date=booking.appointment_date,
            user_id=booking.user_id,
            status=booking.status,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting booking: {str(e)}")


@router.put("/{booking_id}/confirm")
async def confirm_booking(
    booking_id: UUID = Path(..., description="Booking ID"),
    request: BookingActionRequest = BookingActionRequest()
) -> BookingResponse:
    """Confirm a pending booking."""
    try:
        # Use test user if no user_id provided
        user_id = request.user_id or booking_service.get_test_user_id()

        booking = await booking_service.confirm_booking(booking_id, user_id)

        return BookingResponse(
            id=booking.id,
            license_plate=booking.license_plate,
            appointment_date=booking.appointment_date,
            user_id=booking.user_id,
            status=booking.status,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming booking: {str(e)}")


@router.put("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: UUID = Path(..., description="Booking ID"),
    request: BookingActionRequest = BookingActionRequest()
) -> BookingResponse:
    """Cancel a booking."""
    try:
        # Use test user if no user_id provided
        user_id = request.user_id or booking_service.get_test_user_id()

        booking = await booking_service.cancel_booking(booking_id, user_id)

        return BookingResponse(
            id=booking.id,
            license_plate=booking.license_plate,
            appointment_date=booking.appointment_date,
            user_id=booking.user_id,
            status=booking.status,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling booking: {str(e)}")


@router.get("/user/{user_id}")
async def get_user_bookings(
    user_id: UUID = Path(..., description="User ID")
) -> List[BookingResponse]:
    """Get all bookings for a user."""
    try:
        bookings = await booking_service.get_user_bookings(user_id)

        return [
            BookingResponse(
                id=booking.id,
                license_plate=booking.license_plate,
                appointment_date=booking.appointment_date,
                user_id=booking.user_id,
                status=booking.status,
                created_at=booking.created_at,
                updated_at=booking.updated_at
            )
            for booking in bookings
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user bookings: {str(e)}")


@router.get("/")
async def list_bookings() -> dict:
    """List all bookings (demo endpoint)."""
    try:
        # For demo, get test user bookings
        test_user_id = booking_service.get_test_user_id()
        bookings = await booking_service.get_user_bookings(test_user_id)

        booking_responses = [
            BookingResponse(
                id=booking.id,
                license_plate=booking.license_plate,
                appointment_date=booking.appointment_date,
                user_id=booking.user_id,
                status=booking.status,
                created_at=booking.created_at,
                updated_at=booking.updated_at
            )
            for booking in bookings
        ]

        return {
            "bookings": booking_responses,
            "total_count": len(booking_responses),
            "test_user_id": str(test_user_id),
            "message": "Use test_user_id for demo operations"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing bookings: {str(e)}")
