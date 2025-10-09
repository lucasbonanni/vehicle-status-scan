"""Port interfaces for repositories (Dependency Inversion Principle)."""

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.vehicle_inspection.domain.entities.booking import Booking
    from src.vehicle_inspection.domain.entities.vehicle import Vehicle
    from src.vehicle_inspection.domain.entities.inspector import Inspector
    from src.vehicle_inspection.domain.entities.inspection import Inspection
    from src.vehicle_inspection.domain.value_objects.time_slot import TimeSlot
    from src.vehicle_inspection.domain.value_objects.auth import AuthToken


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


class InspectorRepository(ABC):
    """Port interface for inspector repository."""

    @abstractmethod
    async def save(self, inspector: "Inspector") -> "Inspector":
        """Save an inspector."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, inspector_id: UUID) -> Optional["Inspector"]:
        """Find inspector by ID."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional["Inspector"]:
        """Find inspector by email."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_license_number(self, license_number: str) -> Optional["Inspector"]:
        """Find inspector by license number."""
        raise NotImplementedError

    @abstractmethod
    async def find_all_active(self) -> List["Inspector"]:
        """Find all active inspectors."""
        raise NotImplementedError

    @abstractmethod
    async def update_password_hash(self, inspector_id: UUID, password_hash: str) -> bool:
        """Update inspector password hash."""
        raise NotImplementedError

    @abstractmethod
    async def update_login_info(self, inspector_id: UUID, failed_attempts: int = 0, locked_until: Optional[datetime] = None) -> bool:
        """Update inspector login information."""
        raise NotImplementedError

    @abstractmethod
    async def record_login(self, inspector_id: UUID) -> bool:
        """Record successful login."""
        raise NotImplementedError

    @abstractmethod
    async def get_password_hash(self, inspector_id: UUID) -> Optional[str]:
        """Get password hash for inspector."""
        raise NotImplementedError

    @abstractmethod
    async def get_failed_attempts(self, inspector_id: UUID) -> int:
        """Get number of failed login attempts."""
        raise NotImplementedError

    @abstractmethod
    async def get_lockout_expiry(self, inspector_id: UUID) -> Optional[datetime]:
        """Get account lockout expiry time."""
        raise NotImplementedError


class AuthTokenRepository(ABC):
    """Port interface for authentication token repository."""

    @abstractmethod
    async def save_token(self, token: "AuthToken") -> bool:
        """Save authentication token."""
        raise NotImplementedError

    @abstractmethod
    async def find_token(self, token: str) -> Optional["AuthToken"]:
        """Find authentication token."""
        raise NotImplementedError

    @abstractmethod
    async def invalidate_token(self, token: str) -> bool:
        """Invalidate authentication token."""
        raise NotImplementedError

    @abstractmethod
    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens."""
        raise NotImplementedError


class InspectionRepository(ABC):
    """Port interface for inspection repository."""

    @abstractmethod
    async def save(self, inspection: "Inspection") -> "Inspection":
        """Save an inspection (create or update)."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, inspection_id: UUID) -> Optional["Inspection"]:
        """Find inspection by ID."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_license_plate(self, license_plate: str) -> List["Inspection"]:
        """Find all inspections for a license plate (ordered by created_at DESC)."""
        raise NotImplementedError

    @abstractmethod
    async def find_latest_by_license_plate(self, license_plate: str) -> Optional["Inspection"]:
        """Find the most recent inspection for a license plate."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_inspector(self, inspector_id: UUID) -> List["Inspection"]:
        """Find all inspections performed by a specific inspector."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_status(self, status: str) -> List["Inspection"]:
        """Find all inspections with a specific status (draft/completed)."""
        raise NotImplementedError

    @abstractmethod
    async def find_completed_inspections(self, limit: Optional[int] = None) -> List["Inspection"]:
        """Find completed inspections, optionally limited by count."""
        raise NotImplementedError

    @abstractmethod
    async def find_draft_inspections_by_inspector(self, inspector_id: UUID) -> List["Inspection"]:
        """Find all draft inspections for a specific inspector."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, inspection: "Inspection") -> "Inspection":
        """Update an existing inspection."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, inspection_id: UUID) -> bool:
        """Delete an inspection by ID."""
        raise NotImplementedError

    @abstractmethod
    async def exists(self, inspection_id: UUID) -> bool:
        """Check if an inspection exists."""
        raise NotImplementedError

    @abstractmethod
    async def count_by_inspector(self, inspector_id: UUID) -> int:
        """Count total inspections by inspector."""
        raise NotImplementedError

    @abstractmethod
    async def count_by_license_plate(self, license_plate: str) -> int:
        """Count total inspections for a license plate."""
        raise NotImplementedError
