"""Vehicle entity and its inheritance hierarchy."""

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

from ..value_objects.checkpoint_types import CheckpointType
from ..value_objects.safety_result import SafetyResult
from ..value_objects.checkpoint_score import CheckpointScore


class VehicleType(Enum):
    """Vehicle type enumeration."""
    CAR = "car"
    MOTORCYCLE = "motorcycle"


class Vehicle(ABC):
    """Abstract base class for vehicles following OCP and LSP principles."""

    def __init__(
        self,
        license_plate: str,
        make: str,
        model: str,
        year: int,
        created_at: datetime | None = None
    ):
        self._license_plate = license_plate
        self._make = make
        self._model = model
        self._year = year
        self._created_at = created_at or datetime.utcnow()
        self._updated_at = datetime.utcnow()

    @property
    def license_plate(self) -> str:
        """Get vehicle license plate."""
        return self._license_plate

    @property
    def make(self) -> str:
        """Get vehicle make."""
        return self._make

    @property
    def model(self) -> str:
        """Get vehicle model."""
        return self._model

    @property
    def year(self) -> int:
        """Get vehicle year."""
        return self._year

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get last update timestamp."""
        return self._updated_at

    @abstractmethod
    def get_vehicle_type(self) -> VehicleType:
        """Get the specific vehicle type."""
        pass

    @abstractmethod
    def get_required_checkpoints(self) -> List[CheckpointType]:
        """Get the list of required checkpoints for this vehicle type."""
        pass

    @abstractmethod
    def calculate_safety(self, scores: List[CheckpointScore]) -> SafetyResult:
        """Calculate safety result based on vehicle-specific rules."""
        pass

    def __eq__(self, other: object) -> bool:
        """Check equality based on license plate."""
        if not isinstance(other, Vehicle):
            return False
        return self.license_plate == other.license_plate

    def __hash__(self) -> int:
        """Hash based on license plate."""
        return hash(self.license_plate)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}({self.license_plate})"


class Car(Vehicle):
    """Car entity implementing vehicle-specific inspection rules."""

    def get_vehicle_type(self) -> VehicleType:
        """Get car vehicle type."""
        return VehicleType.CAR

    def get_required_checkpoints(self) -> List[CheckpointType]:
        """Get required checkpoints for car inspection."""
        return [
            CheckpointType.BRAKING_SYSTEM,
            CheckpointType.STEERING_SYSTEM,
            CheckpointType.SUSPENSION_SYSTEM,
            CheckpointType.TIRES,
            CheckpointType.LIGHTING_SYSTEM,
            CheckpointType.GAS_EMISSIONS,
            CheckpointType.ELECTRICAL_SYSTEM,
            CheckpointType.BODY_STRUCTURE,
        ]

    def calculate_safety(self, scores: List[CheckpointScore]) -> SafetyResult:
        """Calculate safety for car with car-specific rules."""
        total_score = sum(score.score for score in scores)
        max_possible_score = len(self.get_required_checkpoints()) * 10

        # Check for individual checkpoint failures
        critical_failures = [score for score in scores if score.score < 5]

        # Determine safety status
        is_safe = total_score >= 64 and not critical_failures  # 80% of 80 points
        requires_reinspection = total_score < 32 or bool(critical_failures)  # 40% of 80 points

        # Generate observation if needed
        observation = ""
        if requires_reinspection:
            if critical_failures:
                critical_items = [f"{failure.checkpoint_type.value}: {failure.score}/10"
                                for failure in critical_failures]
                observation += f"Critical failures in: {', '.join(critical_items)}. "
            if total_score < 32:
                observation += f"Total score too low: {total_score}/{max_possible_score}. "
            observation += "Vehicle requires re-inspection before approval."

        return SafetyResult(
            is_safe=is_safe,
            total_score=total_score,
            max_score=max_possible_score,
            requires_reinspection=requires_reinspection,
            observation=observation.strip()
        )


class Motorcycle(Vehicle):
    """Motorcycle entity implementing vehicle-specific inspection rules."""

    def get_vehicle_type(self) -> VehicleType:
        """Get motorcycle vehicle type."""
        return VehicleType.MOTORCYCLE

    def get_required_checkpoints(self) -> List[CheckpointType]:
        """Get required checkpoints for motorcycle inspection."""
        return [
            CheckpointType.BRAKING_SYSTEM,
            CheckpointType.STEERING_SYSTEM,
            CheckpointType.SUSPENSION_SYSTEM,
            CheckpointType.TIRES,
            CheckpointType.LIGHTING_SYSTEM,
            CheckpointType.GAS_EMISSIONS,
            CheckpointType.ELECTRICAL_SYSTEM,
            CheckpointType.BODY_STRUCTURE,
        ]

    def calculate_safety(self, scores: List[CheckpointScore]) -> SafetyResult:
        """Calculate safety for motorcycle with motorcycle-specific rules."""
        total_score = sum(score.score for score in scores)
        max_possible_score = len(self.get_required_checkpoints()) * 10

        # Check for individual checkpoint failures
        critical_failures = [score for score in scores if score.score < 5]

        # Motorcycle-specific safety rules (can be different from cars)
        is_safe = total_score >= 64 and not critical_failures
        requires_reinspection = total_score < 32 or bool(critical_failures)

        # Generate observation if needed
        observation = ""
        if requires_reinspection:
            if critical_failures:
                critical_items = [f"{failure.checkpoint_type.value}: {failure.score}/10"
                                for failure in critical_failures]
                observation += f"Critical failures in: {', '.join(critical_items)}. "
            if total_score < 32:
                observation += f"Total score too low: {total_score}/{max_possible_score}. "
            observation += "Motorcycle requires re-inspection before approval."

        return SafetyResult(
            is_safe=is_safe,
            total_score=total_score,
            max_score=max_possible_score,
            requires_reinspection=requires_reinspection,
            observation=observation.strip()
        )
