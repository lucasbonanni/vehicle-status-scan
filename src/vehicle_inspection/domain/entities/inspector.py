"""Inspector entity for vehicle inspection system."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional


class InspectorRole(Enum):
    """Inspector role enumeration."""
    JUNIOR = "junior"
    SENIOR = "senior"
    SUPERVISOR = "supervisor"


class InspectorStatus(Enum):
    """Inspector status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Inspector:
    """Inspector entity representing an authorized vehicle inspector."""

    def __init__(
        self,
        email: str,
        first_name: str,
        last_name: str,
        role: InspectorRole,
        license_number: str,
        inspector_id: Optional[UUID] = None,
        status: InspectorStatus = InspectorStatus.ACTIVE,
        phone: Optional[str] = None,
        hire_date: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self._id = inspector_id or uuid4()
        self._email = email.lower().strip()
        self._first_name = first_name.strip()
        self._last_name = last_name.strip()
        self._role = role
        self._license_number = license_number.strip().upper()
        self._status = status
        self._phone = phone.strip() if phone else None
        self._hire_date = hire_date or datetime.utcnow()
        self._created_at = created_at or datetime.utcnow()
        self._updated_at = updated_at or datetime.utcnow()

    @property
    def id(self) -> UUID:
        """Get inspector ID."""
        return self._id

    @property
    def email(self) -> str:
        """Get inspector email."""
        return self._email

    @property
    def first_name(self) -> str:
        """Get inspector first name."""
        return self._first_name

    @property
    def last_name(self) -> str:
        """Get inspector last name."""
        return self._last_name

    @property
    def full_name(self) -> str:
        """Get inspector full name."""
        return f"{self._first_name} {self._last_name}"

    @property
    def role(self) -> InspectorRole:
        """Get inspector role."""
        return self._role

    @property
    def license_number(self) -> str:
        """Get inspector license number."""
        return self._license_number

    @property
    def status(self) -> InspectorStatus:
        """Get inspector status."""
        return self._status

    @property
    def phone(self) -> Optional[str]:
        """Get inspector phone."""
        return self._phone

    @property
    def hire_date(self) -> datetime:
        """Get inspector hire date."""
        return self._hire_date

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get last update timestamp."""
        return self._updated_at

    def is_active(self) -> bool:
        """Check if inspector is active."""
        return self._status == InspectorStatus.ACTIVE

    def can_perform_inspections(self) -> bool:
        """Check if inspector can perform inspections."""
        return self.is_active()

    def is_supervisor(self) -> bool:
        """Check if inspector has supervisor role."""
        return self._role == InspectorRole.SUPERVISOR

    def can_supervise(self) -> bool:
        """Check if inspector can supervise other inspectors."""
        return self.is_active() and self.is_supervisor()

    def activate(self) -> None:
        """Activate inspector."""
        self._status = InspectorStatus.ACTIVE
        self._updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate inspector."""
        self._status = InspectorStatus.INACTIVE
        self._updated_at = datetime.utcnow()

    def suspend(self) -> None:
        """Suspend inspector."""
        self._status = InspectorStatus.SUSPENDED
        self._updated_at = datetime.utcnow()

    def update_role(self, new_role: InspectorRole) -> None:
        """Update inspector role."""
        self._role = new_role
        self._updated_at = datetime.utcnow()

    def update_contact_info(self, phone: Optional[str] = None) -> None:
        """Update inspector contact information."""
        if phone is not None:
            self._phone = phone.strip() if phone else None
        self._updated_at = datetime.utcnow()

    def __eq__(self, other) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, Inspector):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self._id)

    def __str__(self) -> str:
        """String representation."""
        return f"Inspector({self.full_name}, {self.role.value}, {self.license_number})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"Inspector(id={self._id}, email='{self._email}', "
                f"name='{self.full_name}', role='{self._role.value}', "
                f"license='{self._license_number}', status='{self._status.value}')")
