"""Port interfaces for repositories (Dependency Inversion Principle)."""

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.vehicle_inspection.domain.entities.booking import Booking
    from src.vehicle_inspection.domain.entities.vehicle import Vehicle
    from src.vehicle_inspection.domain.value_objects.time_slot import TimeSlot


class BookingRepository(ABC):
    """Port interface for booking repository."""

    @abstractmethod
    async def save(self, booking: "Booking") -> "Booking":
        """Save a booking."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, booking_id: UUID) -> Optional["Booking"]:
        """Find booking by ID."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_license_plate(self, license_plate: str) -> List["Booking"]:
        """Find all bookings for a license plate."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> List["Booking"]:
        """Find all bookings for a user."""
        raise NotImplementedError

    @abstractmethod
    async def find_available_slots(self, target_date: date) -> List["TimeSlot"]:
        """Find available time slots for a specific date."""
        raise NotImplementedError

    @abstractmethod
    async def is_slot_available(self, appointment_date: datetime) -> bool:
        """Check if a specific datetime slot is available."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, booking_id: UUID) -> bool:
        """Delete a booking."""
        raise NotImplementedError


class VehicleRepository(ABC):
    """Port interface for vehicle repository."""

    @abstractmethod
    async def save(self, vehicle: "Vehicle") -> "Vehicle":
        """Save a vehicle."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_license_plate(self, license_plate: str) -> Optional["Vehicle"]:
        """Find vehicle by license plate."""
        raise NotImplementedError

    @abstractmethod
    async def find_all(self) -> List["Vehicle"]:
        """Find all vehicles."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, license_plate: str) -> bool:
        """Delete a vehicle."""
        raise NotImplementedError


class UserRepository(ABC):
    """Port interface for user repository."""

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[dict]:
        """Find user by ID."""
        raise NotImplementedError

    @abstractmethod
    async def exists(self, user_id: UUID) -> bool:
        """Check if user exists."""
        raise NotImplementedError
