"""Booking entity for appointment management."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional


class BookingStatus(Enum):
    """Booking status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Booking:
    """Booking entity representing a vehicle inspection appointment."""

    def __init__(
        self,
        license_plate: str,
        appointment_date: datetime,
        user_id: UUID,
        booking_id: Optional[UUID] = None,
        status: BookingStatus = BookingStatus.PENDING,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self._id = booking_id or uuid4()
        self._license_plate = license_plate
        self._appointment_date = appointment_date
        self._user_id = user_id
        self._status = status
        self._created_at = created_at or datetime.utcnow()
        self._updated_at = updated_at or datetime.utcnow()

    @property
    def id(self) -> UUID:
        """Get booking ID."""
        return self._id

    @property
    def license_plate(self) -> str:
        """Get vehicle license plate."""
        return self._license_plate

    @property
    def appointment_date(self) -> datetime:
        """Get appointment date."""
        return self._appointment_date

    @property
    def user_id(self) -> UUID:
        """Get user ID."""
        return self._user_id

    @property
    def status(self) -> BookingStatus:
        """Get booking status."""
        return self._status

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get last update timestamp."""
        return self._updated_at

    def confirm(self) -> None:
        """Confirm the booking."""
        if self._status != BookingStatus.PENDING:
            raise ValueError("Only pending bookings can be confirmed")
        self._status = BookingStatus.CONFIRMED
        self._updated_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel the booking."""
        if self._status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
            raise ValueError("Cannot cancel completed or already cancelled bookings")
        self._status = BookingStatus.CANCELLED
        self._updated_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark booking as completed."""
        if self._status != BookingStatus.CONFIRMED:
            raise ValueError("Only confirmed bookings can be completed")
        self._status = BookingStatus.COMPLETED
        self._updated_at = datetime.utcnow()

    def is_editable(self) -> bool:
        """Check if booking can be modified."""
        return self._status in [BookingStatus.PENDING, BookingStatus.CONFIRMED]

    def __eq__(self, other: object) -> bool:
        """Check equality based on booking ID."""
        if not isinstance(other, Booking):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Hash based on booking ID."""
        return hash(self._id)

    def __str__(self) -> str:
        """String representation."""
        return f"Booking({self._id}, {self._license_plate}, {self._status.value})"
