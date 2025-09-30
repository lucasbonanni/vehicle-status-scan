"""Booking endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_bookings() -> dict[str, str]:
    """List all bookings (placeholder)."""
    return {"message": "Booking endpoints - coming soon"}


@router.post("/")
async def create_booking() -> dict[str, str]:
    """Create new booking (placeholder)."""
    return {"message": "Create booking - coming soon"}


@router.get("/{booking_id}")
async def get_booking(booking_id: str) -> dict[str, str]:
    """Get booking by ID (placeholder)."""
    return {"message": f"Get booking {booking_id} - coming soon"}
