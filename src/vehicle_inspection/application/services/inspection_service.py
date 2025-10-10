"""Inspection service implementing business logic for vehicle inspections."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, TYPE_CHECKING
from uuid import UUID

from src.vehicle_inspection.domain.entities.inspection import Inspection, InspectionStatus
from src.vehicle_inspection.domain.entities.vehicle import VehicleType, Car, Motorcycle
from src.vehicle_inspection.domain.value_objects.checkpoint_score import CheckpointScore
from src.vehicle_inspection.domain.value_objects.checkpoint_types import CheckpointType
from src.vehicle_inspection.domain.value_objects.safety_result import SafetyResult
from src.vehicle_inspection.infrastructure.logging import (
    get_logger,
    log_business_rule_violation,
    log_with_extra
)

if TYPE_CHECKING:
    from src.vehicle_inspection.application.ports.repositories import InspectionRepository, InspectorRepository


class InspectionService:
    """Service for managing vehicle inspections and business logic."""

    def __init__(
        self,
        inspection_repository: "InspectionRepository",
        inspector_repository: "InspectorRepository"
    ):
        """Initialize inspection service with repository dependencies."""
        self._inspection_repository = inspection_repository
        self._inspector_repository = inspector_repository
        self._logger = get_logger(__name__)

    async def create_inspection(
        self,
        license_plate: str,
        vehicle_type: VehicleType,
        inspector_id: UUID
    ) -> Inspection:
        """Create a new inspection in draft status.

        Args:
            license_plate: Vehicle license plate
            vehicle_type: Type of vehicle (car or motorcycle)
            inspector_id: ID of the inspector creating the inspection

        Returns:
            Created inspection entity

        Raises:
            ValueError: If input validation fails
            RuntimeError: If inspector not found or inactive
        """
        self._logger.info(f"Creating inspection for license plate {license_plate} by inspector {inspector_id}")

        # Validate inputs
        if not license_plate or not license_plate.strip():
            self._logger.warning("Attempted to create inspection with empty license plate")
            raise ValueError("License plate cannot be empty")

        if not isinstance(vehicle_type, VehicleType):
            self._logger.warning(f"Invalid vehicle type provided: {type(vehicle_type)}")
            raise ValueError("Vehicle type must be a VehicleType enum")

        # Validate inspector exists and is active
        inspector = await self._inspector_repository.find_by_id(inspector_id)
        if not inspector:
            self._logger.error(f"Inspector {inspector_id} not found when creating inspection")
            raise RuntimeError(f"Inspector with ID {inspector_id} not found")

        if not inspector.can_perform_inspections():
            log_business_rule_violation(
                self._logger,
                "inspector_not_authorized",
                f"Inspector {inspector_id} attempted to create inspection but is not authorized",
                inspector_id=str(inspector_id),
                inspector_status=inspector.status.value if hasattr(inspector.status, 'value') else str(inspector.status)
            )
            raise RuntimeError(f"Inspector {inspector_id} is not authorized to perform inspections")

        # Normalize license plate
        normalized_plate = self._normalize_license_plate(license_plate)

        # Create new inspection entity
        inspection = Inspection(
            license_plate=normalized_plate,
            vehicle_type=vehicle_type,
            inspector_id=inspector_id,
            status=InspectionStatus.DRAFT
        )

        # Save to repository
        saved_inspection = await self._inspection_repository.save(inspection)

        log_with_extra(
            self._logger,
            logging.INFO,
            f"Inspection created successfully for {normalized_plate}",
            inspection_id=str(saved_inspection.id),
            license_plate=normalized_plate,
            vehicle_type=vehicle_type.value,
            inspector_id=str(inspector_id),
            status=InspectionStatus.DRAFT.value
        )

        return saved_inspection

    async def update_checkpoint_scores(
        self,
        inspection_id: UUID,
        checkpoint_scores: List[CheckpointScore]
    ) -> Inspection:
        """Update checkpoint scores for an inspection.

        Args:
            inspection_id: ID of the inspection to update
            checkpoint_scores: List of checkpoint scores to update

        Returns:
            Updated inspection entity

        Raises:
            ValueError: If inspection not found or completed
            RuntimeError: If business rules violated
        """
        self._logger.info(f"Updating checkpoint scores for inspection {inspection_id}")

        # Find inspection
        inspection = await self._inspection_repository.find_by_id(inspection_id)
        if not inspection:
            self._logger.error(f"Inspection {inspection_id} not found for score update")
            raise ValueError(f"Inspection with ID {inspection_id} not found")

        # Validate inspection can be modified
        if inspection.status == InspectionStatus.COMPLETED:
            log_business_rule_violation(
                self._logger,
                "modify_completed_inspection",
                f"Attempted to modify scores for completed inspection {inspection_id}",
                inspection_id=str(inspection_id),
                license_plate=inspection.license_plate
            )
            raise ValueError("Cannot modify checkpoint scores for completed inspection")

        # Validate checkpoint scores
        self._validate_checkpoint_scores(checkpoint_scores, inspection.vehicle_type)

        # Update checkpoint scores in the inspection entity
        inspection.update_checkpoint_scores(checkpoint_scores)

        # Save updated inspection
        updated_inspection = await self._inspection_repository.update(inspection)

        log_with_extra(
            self._logger,
            logging.INFO,
            f"Checkpoint scores updated for inspection {inspection_id}",
            inspection_id=str(inspection_id),
            license_plate=inspection.license_plate,
            checkpoint_count=len(checkpoint_scores),
            vehicle_type=inspection.vehicle_type.value
        )

        return updated_inspection

    async def complete_inspection(
        self,
        inspection_id: UUID,
        observations: Optional[str] = None
    ) -> Inspection:
        """Complete an inspection and calculate final safety result.

        Args:
            inspection_id: ID of the inspection to complete
            observations: Optional inspector observations

        Returns:
            Completed inspection entity

        Raises:
            ValueError: If inspection not found or cannot be completed
            RuntimeError: If business rules violated
        """
        self._logger.info(f"Completing inspection {inspection_id}")

        # Find inspection
        inspection = await self._inspection_repository.find_by_id(inspection_id)
        if not inspection:
            self._logger.error(f"Inspection {inspection_id} not found for completion")
            raise ValueError(f"Inspection with ID {inspection_id} not found")

        # Validate inspection can be completed
        if inspection.status == InspectionStatus.COMPLETED:
            log_business_rule_violation(
                self._logger,
                "complete_already_completed_inspection",
                f"Attempted to complete already completed inspection {inspection_id}",
                inspection_id=str(inspection_id),
                license_plate=inspection.license_plate
            )
            raise ValueError("Inspection is already completed")

        # Validate all required checkpoints have scores
        required_checkpoints = self._get_required_checkpoints(inspection.vehicle_type)
        current_checkpoints = {score.checkpoint_type for score in inspection.checkpoint_scores}

        missing_checkpoints = required_checkpoints - current_checkpoints
        if missing_checkpoints:
            missing_names = [cp.value for cp in missing_checkpoints]
            log_business_rule_violation(
                self._logger,
                "incomplete_checkpoint_scores",
                f"Attempted to complete inspection {inspection_id} with missing checkpoints: {missing_names}",
                inspection_id=str(inspection_id),
                license_plate=inspection.license_plate,
                missing_checkpoints=missing_names
            )
            raise ValueError(f"Missing required checkpoint scores: {', '.join(missing_names)}")

        # Update observations if provided
        if observations is not None:
            inspection.update_observations(observations.strip())

        # Complete the inspection (this will calculate safety result)
        inspection.complete_inspection()

        # Save completed inspection
        completed_inspection = await self._inspection_repository.update(inspection)

        # Log completion with safety result
        safety_result = completed_inspection.calculate_safety_result()
        log_with_extra(
            self._logger,
            logging.INFO,
            f"Inspection {inspection_id} completed successfully",
            inspection_id=str(inspection_id),
            license_plate=inspection.license_plate,
            vehicle_type=inspection.vehicle_type.value,
            is_safe=safety_result.is_safe,
            requires_reinspection=safety_result.requires_reinspection,
            total_score=safety_result.total_score,
            inspector_id=str(inspection.inspector_id)
        )

        return completed_inspection

    async def get_inspection_by_id(self, inspection_id: UUID) -> Optional[Inspection]:
        """Get inspection by ID.

        Args:
            inspection_id: ID of the inspection

        Returns:
            Inspection entity or None if not found
        """
        return await self._inspection_repository.find_by_id(inspection_id)

    async def get_inspections_by_license_plate(self, license_plate: str) -> List[Inspection]:
        """Get all inspections for a license plate, ordered by most recent first.

        Args:
            license_plate: Vehicle license plate

        Returns:
            List of inspection entities
        """
        if not license_plate or not license_plate.strip():
            raise ValueError("License plate cannot be empty")

        normalized_plate = self._normalize_license_plate(license_plate)
        return await self._inspection_repository.find_by_license_plate(normalized_plate)

    async def get_latest_inspection_by_license_plate(self, license_plate: str) -> Optional[Inspection]:
        """Get the most recent inspection for a license plate.

        Args:
            license_plate: Vehicle license plate

        Returns:
            Most recent inspection entity or None if no inspections found
        """
        if not license_plate or not license_plate.strip():
            raise ValueError("License plate cannot be empty")

        normalized_plate = self._normalize_license_plate(license_plate)
        return await self._inspection_repository.find_latest_by_license_plate(normalized_plate)

    async def get_inspections_by_inspector(self, inspector_id: UUID) -> List[Inspection]:
        """Get all inspections performed by an inspector.

        Args:
            inspector_id: ID of the inspector

        Returns:
            List of inspection entities
        """
        return await self._inspection_repository.find_by_inspector(inspector_id)

    async def get_draft_inspections_by_inspector(self, inspector_id: UUID) -> List[Inspection]:
        """Get all draft inspections for an inspector.

        Args:
            inspector_id: ID of the inspector

        Returns:
            List of draft inspection entities
        """
        return await self._inspection_repository.find_draft_inspections_by_inspector(inspector_id)

    async def get_completed_inspections(self, limit: Optional[int] = None) -> List[Inspection]:
        """Get completed inspections, optionally limited by count.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of completed inspection entities
        """
        return await self._inspection_repository.find_completed_inspections(limit)

    def _normalize_license_plate(self, license_plate: str) -> str:
        """Normalize license plate for consistent storage and querying."""
        return license_plate.strip().upper().replace(" ", "").replace("-", "")

    def _validate_checkpoint_scores(self, scores: List[CheckpointScore], vehicle_type: VehicleType) -> None:
        """Validate checkpoint scores for business rules.

        Args:
            scores: List of checkpoint scores to validate
            vehicle_type: Type of vehicle being inspected

        Raises:
            ValueError: If validation fails
        """
        if not scores:
            raise ValueError("Checkpoint scores cannot be empty")

        # Check for duplicate checkpoint types
        checkpoint_types = [score.checkpoint_type for score in scores]
        if len(checkpoint_types) != len(set(checkpoint_types)):
            raise ValueError("Duplicate checkpoint types found in scores")

        # Validate each score is within valid range (1-10)
        for score in scores:
            if not isinstance(score, CheckpointScore):
                raise ValueError("All scores must be CheckpointScore instances")

        # Validate all checkpoints are applicable to vehicle type
        required_checkpoints = self._get_required_checkpoints(vehicle_type)
        for score in scores:
            if score.checkpoint_type not in required_checkpoints:
                raise ValueError(f"Checkpoint {score.checkpoint_type.value} is not applicable to {vehicle_type.value}")

    def _get_required_checkpoints(self, vehicle_type: VehicleType) -> set[CheckpointType]:
        """Get required checkpoint types for a vehicle type.

        Args:
            vehicle_type: Type of vehicle

        Returns:
            Set of required checkpoint types
        """
        # Create a temporary vehicle instance to get required checkpoints
        if vehicle_type == VehicleType.CAR:
            vehicle = Car("TEMP123", "Temp", "Model", 2023)
        elif vehicle_type == VehicleType.MOTORCYCLE:
            vehicle = Motorcycle("TEMP123", "Temp", "Model", 2023)
        else:
            raise ValueError(f"Unsupported vehicle type: {vehicle_type}")

        return set(vehicle.get_required_checkpoints())

    async def calculate_safety_result(
        self,
        checkpoint_scores: List[CheckpointScore],
        vehicle_type: VehicleType
    ) -> SafetyResult:
        """Calculate safety result for given checkpoint scores.

        This is a utility method for preview calculations without saving.

        Args:
            checkpoint_scores: List of checkpoint scores
            vehicle_type: Type of vehicle

        Returns:
            Calculated safety result
        """
        # Create temporary vehicle instance for calculation
        if vehicle_type == VehicleType.CAR:
            vehicle = Car("TEMP123", "Temp", "Model", 2023)
        elif vehicle_type == VehicleType.MOTORCYCLE:
            vehicle = Motorcycle("TEMP123", "Temp", "Model", 2023)
        else:
            raise ValueError(f"Unsupported vehicle type: {vehicle_type}")

        # Calculate safety result using vehicle's logic
        return vehicle.calculate_safety_result(checkpoint_scores)
