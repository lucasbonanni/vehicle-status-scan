"""Inspection entity for vehicle inspection system."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from uuid import UUID, uuid4

from ..value_objects.checkpoint_score import CheckpointScore
from ..value_objects.checkpoint_types import CheckpointType
from ..value_objects.safety_result import SafetyResult
from .vehicle import VehicleType


class InspectionStatus(Enum):
    """Inspection status enumeration."""
    DRAFT = "draft"
    COMPLETED = "completed"


class Inspection:
    """Inspection entity representing a vehicle inspection report."""

    def __init__(
        self,
        license_plate: str,
        vehicle_type: VehicleType,
        inspector_id: UUID,
        inspection_id: Optional[UUID] = None,
        checkpoint_scores: Optional[List[CheckpointScore]] = None,
        observations: str = "",
        status: InspectionStatus = InspectionStatus.DRAFT,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """Initialize inspection entity."""
        # Validate required fields
        if not license_plate or not license_plate.strip():
            raise ValueError("License plate cannot be empty")
        if not isinstance(vehicle_type, VehicleType):
            raise ValueError("Vehicle type must be a VehicleType enum")
        if not isinstance(inspector_id, UUID):
            raise ValueError("Inspector ID must be a UUID")

        self._id = inspection_id or uuid4()
        self._license_plate = license_plate.strip().upper()
        self._vehicle_type = vehicle_type
        self._inspector_id = inspector_id
        self._checkpoint_scores = checkpoint_scores or []
        self._observations = observations.strip()
        self._status = status
        self._created_at = created_at or datetime.utcnow()
        self._updated_at = updated_at or datetime.utcnow()

        # Validate checkpoint scores if provided
        self._validate_checkpoint_scores()

    @property
    def id(self) -> UUID:
        """Get inspection ID."""
        return self._id

    @property
    def license_plate(self) -> str:
        """Get vehicle license plate."""
        return self._license_plate

    @property
    def vehicle_type(self) -> VehicleType:
        """Get vehicle type."""
        return self._vehicle_type

    @property
    def inspector_id(self) -> UUID:
        """Get inspector ID."""
        return self._inspector_id

    @property
    def checkpoint_scores(self) -> List[CheckpointScore]:
        """Get checkpoint scores."""
        return self._checkpoint_scores.copy()

    @property
    def observations(self) -> str:
        """Get inspector observations."""
        return self._observations

    @property
    def status(self) -> InspectionStatus:
        """Get inspection status."""
        return self._status

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get last update timestamp."""
        return self._updated_at

    def update_checkpoint_scores(self, scores: List[CheckpointScore]) -> None:
        """Update checkpoint scores."""
        if self._status == InspectionStatus.COMPLETED:
            raise ValueError("Cannot update scores for completed inspection")

        # Validate scores
        if not isinstance(scores, list):
            raise ValueError("Scores must be a list")

        # Create a copy to avoid modifying the original
        new_scores = scores.copy()

        # Validate each score
        for score in new_scores:
            if not isinstance(score, CheckpointScore):
                raise ValueError("All scores must be CheckpointScore instances")

        self._checkpoint_scores = new_scores
        self._updated_at = datetime.utcnow()

        # Validate the updated scores
        self._validate_checkpoint_scores()

    def add_checkpoint_score(self, score: CheckpointScore) -> None:
        """Add or update a single checkpoint score."""
        if self._status == InspectionStatus.COMPLETED:
            raise ValueError("Cannot update scores for completed inspection")

        if not isinstance(score, CheckpointScore):
            raise ValueError("Score must be a CheckpointScore instance")

        # Remove existing score for this checkpoint type if it exists
        self._checkpoint_scores = [
            s for s in self._checkpoint_scores
            if s.checkpoint_type != score.checkpoint_type
        ]

        # Add the new score
        self._checkpoint_scores.append(score)
        self._updated_at = datetime.utcnow()

    def update_observations(self, observations: str) -> None:
        """Update inspector observations."""
        if self._status == InspectionStatus.COMPLETED:
            raise ValueError("Cannot update observations for completed inspection")

        self._observations = observations.strip()
        self._updated_at = datetime.utcnow()

    def complete_inspection(self, final_observations: Optional[str] = None) -> None:
        """Complete the inspection."""
        if self._status == InspectionStatus.COMPLETED:
            raise ValueError("Inspection is already completed")

        # Validate that all required checkpoints have scores
        if not self._has_all_required_checkpoints():
            missing_checkpoints = self._get_missing_checkpoints()
            raise ValueError(
                f"Cannot complete inspection. Missing scores for: {', '.join(missing_checkpoints)}"
            )

        if final_observations is not None:
            self._observations = final_observations.strip()

        self._status = InspectionStatus.COMPLETED
        self._updated_at = datetime.utcnow()

    def calculate_safety_result(self) -> SafetyResult:
        """Calculate safety result based on checkpoint scores."""
        if not self._checkpoint_scores:
            raise ValueError("Cannot calculate safety result without checkpoint scores")

        # Import here to avoid circular imports
        from .vehicle import Car, Motorcycle

        # Create a vehicle instance to use its safety calculation
        if self._vehicle_type == VehicleType.CAR:
            vehicle = Car(
                license_plate=self._license_plate,
                make="Unknown",  # Placeholder for calculation
                model="Unknown",  # Placeholder for calculation
                year=2020  # Placeholder for calculation
            )
        else:  # VehicleType.MOTORCYCLE
            vehicle = Motorcycle(
                license_plate=self._license_plate,
                make="Unknown",  # Placeholder for calculation
                model="Unknown",  # Placeholder for calculation
                year=2020  # Placeholder for calculation
            )

        return vehicle.calculate_safety(self._checkpoint_scores)

    def get_total_score(self) -> int:
        """Get total score from all checkpoints."""
        return sum(score.score for score in self._checkpoint_scores)

    def get_max_possible_score(self) -> int:
        """Get maximum possible score."""
        return len(self._get_required_checkpoints()) * 10

    def has_critical_failures(self) -> bool:
        """Check if inspection has any critical failures (scores < 5)."""
        return any(score.is_critical_failure for score in self._checkpoint_scores)

    def get_checkpoint_score(self, checkpoint_type: CheckpointType) -> Optional[CheckpointScore]:
        """Get score for a specific checkpoint type."""
        for score in self._checkpoint_scores:
            if score.checkpoint_type == checkpoint_type:
                return score
        return None

    def is_editable(self) -> bool:
        """Check if inspection can be modified."""
        return self._status == InspectionStatus.DRAFT

    def is_completed(self) -> bool:
        """Check if inspection is completed."""
        return self._status == InspectionStatus.COMPLETED

    def get_scores_by_checkpoint(self) -> Dict[CheckpointType, CheckpointScore]:
        """Get scores organized by checkpoint type."""
        return {score.checkpoint_type: score for score in self._checkpoint_scores}

    def _validate_checkpoint_scores(self) -> None:
        """Validate checkpoint scores consistency."""
        # Check for duplicate checkpoint types
        checkpoint_types = [score.checkpoint_type for score in self._checkpoint_scores]
        if len(checkpoint_types) != len(set(checkpoint_types)):
            raise ValueError("Duplicate checkpoint types found in scores")

        # Validate that all checkpoint types are valid for this vehicle type
        required_checkpoints = self._get_required_checkpoints()
        for score in self._checkpoint_scores:
            if score.checkpoint_type not in required_checkpoints:
                raise ValueError(
                    f"Checkpoint {score.checkpoint_type.value} is not valid for vehicle type {self._vehicle_type.value}"
                )

    def _get_required_checkpoints(self) -> List[CheckpointType]:
        """Get required checkpoints for this vehicle type."""
        # All vehicles use the same 8 checkpoints for now
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

    def _has_all_required_checkpoints(self) -> bool:
        """Check if all required checkpoints have scores."""
        required_checkpoints = set(self._get_required_checkpoints())
        scored_checkpoints = {score.checkpoint_type for score in self._checkpoint_scores}
        return required_checkpoints.issubset(scored_checkpoints)

    def _get_missing_checkpoints(self) -> List[str]:
        """Get list of missing checkpoint names."""
        required_checkpoints = set(self._get_required_checkpoints())
        scored_checkpoints = {score.checkpoint_type for score in self._checkpoint_scores}
        missing = required_checkpoints - scored_checkpoints
        return [checkpoint.value for checkpoint in missing]

    def __eq__(self, other: object) -> bool:
        """Check equality based on inspection ID."""
        if not isinstance(other, Inspection):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Hash based on inspection ID."""
        return hash(self._id)

    def __str__(self) -> str:
        """String representation."""
        return f"Inspection({self._id}, {self._license_plate}, {self._status.value})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Inspection(id={self._id}, license_plate='{self._license_plate}', "
            f"vehicle_type={self._vehicle_type.value}, inspector_id={self._inspector_id}, "
            f"status={self._status.value}, scores_count={len(self._checkpoint_scores)}, "
            f"created_at={self._created_at.isoformat()})"
        )
