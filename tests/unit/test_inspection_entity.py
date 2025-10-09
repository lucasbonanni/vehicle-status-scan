"""Unit tests for Inspection domain entity."""

import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from src.vehicle_inspection.domain.entities.inspection import Inspection, InspectionStatus
from src.vehicle_inspection.domain.entities.vehicle import VehicleType
from src.vehicle_inspection.domain.value_objects.checkpoint_score import CheckpointScore
from src.vehicle_inspection.domain.value_objects.checkpoint_types import CheckpointType


class TestInspection:
    """Test cases for Inspection entity."""

    def test_inspection_creation_with_required_fields(self):
        """Test creating inspection with required fields."""
        inspector_id = uuid4()
        inspection = Inspection(
            license_plate="ABC123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id
        )

        assert inspection.license_plate == "ABC123"
        assert inspection.vehicle_type == VehicleType.CAR
        assert inspection.inspector_id == inspector_id
        assert inspection.status == InspectionStatus.DRAFT
        assert inspection.observations == ""
        assert len(inspection.checkpoint_scores) == 0
        assert isinstance(inspection.id, UUID)
        assert isinstance(inspection.created_at, datetime)
        assert isinstance(inspection.updated_at, datetime)

    def test_inspection_creation_with_all_fields(self):
        """Test creating inspection with all fields."""
        inspector_id = uuid4()
        inspection_id = uuid4()
        created_at = datetime.utcnow() - timedelta(hours=1)
        updated_at = datetime.utcnow()

        scores = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8, "Good condition"),
            CheckpointScore(CheckpointType.TIRES, 7, "Minor wear")
        ]

        inspection = Inspection(
            license_plate="XYZ789",
            vehicle_type=VehicleType.MOTORCYCLE,
            inspector_id=inspector_id,
            inspection_id=inspection_id,
            checkpoint_scores=scores,
            observations="Initial inspection notes",
            status=InspectionStatus.DRAFT,
            created_at=created_at,
            updated_at=updated_at
        )

        assert inspection.id == inspection_id
        assert inspection.license_plate == "XYZ789"
        assert inspection.vehicle_type == VehicleType.MOTORCYCLE
        assert inspection.inspector_id == inspector_id
        assert len(inspection.checkpoint_scores) == 2
        assert inspection.observations == "Initial inspection notes"
        assert inspection.status == InspectionStatus.DRAFT
        assert inspection.created_at == created_at
        assert inspection.updated_at == updated_at

    def test_license_plate_validation(self):
        """Test license plate validation."""
        inspector_id = uuid4()

        # Empty license plate should raise error
        with pytest.raises(ValueError, match="License plate cannot be empty"):
            Inspection("", VehicleType.CAR, inspector_id)

        # Whitespace-only license plate should raise error
        with pytest.raises(ValueError, match="License plate cannot be empty"):
            Inspection("   ", VehicleType.CAR, inspector_id)

    def test_license_plate_normalization(self):
        """Test license plate is normalized to uppercase and trimmed."""
        inspector_id = uuid4()
        inspection = Inspection("  abc123  ", VehicleType.CAR, inspector_id)
        assert inspection.license_plate == "ABC123"

    def test_vehicle_type_validation(self):
        """Test vehicle type validation."""
        inspector_id = uuid4()

        with pytest.raises(ValueError, match="Vehicle type must be a VehicleType enum"):
            Inspection("ABC123", "car", inspector_id)

    def test_inspector_id_validation(self):
        """Test inspector ID validation."""
        with pytest.raises(ValueError, match="Inspector ID must be a UUID"):
            Inspection("ABC123", VehicleType.CAR, "not-a-uuid")

    def test_add_checkpoint_score(self):
        """Test adding checkpoint scores."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        score = CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8, "Good")
        inspection.add_checkpoint_score(score)

        assert len(inspection.checkpoint_scores) == 1
        assert inspection.checkpoint_scores[0] == score
        assert inspection.get_checkpoint_score(CheckpointType.BRAKING_SYSTEM) == score

    def test_add_duplicate_checkpoint_score_replaces_existing(self):
        """Test that adding duplicate checkpoint type replaces existing score."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        score1 = CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8, "Good")
        score2 = CheckpointScore(CheckpointType.BRAKING_SYSTEM, 6, "Fair")

        inspection.add_checkpoint_score(score1)
        inspection.add_checkpoint_score(score2)

        assert len(inspection.checkpoint_scores) == 1
        assert inspection.get_checkpoint_score(CheckpointType.BRAKING_SYSTEM) == score2

    def test_update_checkpoint_scores(self):
        """Test updating all checkpoint scores."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        scores = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8, "Good"),
            CheckpointScore(CheckpointType.TIRES, 7, "Fair"),
            CheckpointScore(CheckpointType.LIGHTING_SYSTEM, 9, "Excellent")
        ]

        inspection.update_checkpoint_scores(scores)

        assert len(inspection.checkpoint_scores) == 3
        assert inspection.get_total_score() == 24

    def test_update_observations(self):
        """Test updating observations."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        inspection.update_observations("New observations")
        assert inspection.observations == "New observations"

        # Test trimming whitespace
        inspection.update_observations("  Trimmed observations  ")
        assert inspection.observations == "Trimmed observations"

    def test_complete_inspection_success(self):
        """Test completing inspection with all required scores."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        # Add all required checkpoint scores
        all_scores = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8),
            CheckpointScore(CheckpointType.STEERING_SYSTEM, 7),
            CheckpointScore(CheckpointType.SUSPENSION_SYSTEM, 9),
            CheckpointScore(CheckpointType.TIRES, 6),
            CheckpointScore(CheckpointType.LIGHTING_SYSTEM, 8),
            CheckpointScore(CheckpointType.GAS_EMISSIONS, 7),
            CheckpointScore(CheckpointType.ELECTRICAL_SYSTEM, 9),
            CheckpointScore(CheckpointType.BODY_STRUCTURE, 8)
        ]

        inspection.update_checkpoint_scores(all_scores)
        inspection.complete_inspection("Final inspection complete")

        assert inspection.status == InspectionStatus.COMPLETED
        assert inspection.observations == "Final inspection complete"
        assert not inspection.is_editable()
        assert inspection.is_completed()

    def test_complete_inspection_missing_scores(self):
        """Test completing inspection fails when missing required scores."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        # Add only partial scores
        partial_scores = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8),
            CheckpointScore(CheckpointType.TIRES, 7)
        ]

        inspection.update_checkpoint_scores(partial_scores)

        with pytest.raises(ValueError, match="Cannot complete inspection. Missing scores for"):
            inspection.complete_inspection()

    def test_complete_inspection_already_completed(self):
        """Test completing already completed inspection fails."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        # Add all required scores and complete
        all_scores = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8),
            CheckpointScore(CheckpointType.STEERING_SYSTEM, 7),
            CheckpointScore(CheckpointType.SUSPENSION_SYSTEM, 9),
            CheckpointScore(CheckpointType.TIRES, 6),
            CheckpointScore(CheckpointType.LIGHTING_SYSTEM, 8),
            CheckpointScore(CheckpointType.GAS_EMISSIONS, 7),
            CheckpointScore(CheckpointType.ELECTRICAL_SYSTEM, 9),
            CheckpointScore(CheckpointType.BODY_STRUCTURE, 8)
        ]

        inspection.update_checkpoint_scores(all_scores)
        inspection.complete_inspection()

        with pytest.raises(ValueError, match="Inspection is already completed"):
            inspection.complete_inspection()

    def test_cannot_modify_completed_inspection(self):
        """Test that completed inspections cannot be modified."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        # Complete the inspection first
        all_scores = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8),
            CheckpointScore(CheckpointType.STEERING_SYSTEM, 7),
            CheckpointScore(CheckpointType.SUSPENSION_SYSTEM, 9),
            CheckpointScore(CheckpointType.TIRES, 6),
            CheckpointScore(CheckpointType.LIGHTING_SYSTEM, 8),
            CheckpointScore(CheckpointType.GAS_EMISSIONS, 7),
            CheckpointScore(CheckpointType.ELECTRICAL_SYSTEM, 9),
            CheckpointScore(CheckpointType.BODY_STRUCTURE, 8)
        ]

        inspection.update_checkpoint_scores(all_scores)
        inspection.complete_inspection()

        # Now try to modify - should fail
        new_score = CheckpointScore(CheckpointType.BRAKING_SYSTEM, 9)

        with pytest.raises(ValueError, match="Cannot update scores for completed inspection"):
            inspection.add_checkpoint_score(new_score)

        with pytest.raises(ValueError, match="Cannot update scores for completed inspection"):
            inspection.update_checkpoint_scores([new_score])

        with pytest.raises(ValueError, match="Cannot update observations for completed inspection"):
            inspection.update_observations("New observations")

    def test_calculate_safety_result(self):
        """Test safety result calculation."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        # Add scores that should result in safe vehicle
        safe_scores = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8),
            CheckpointScore(CheckpointType.STEERING_SYSTEM, 8),
            CheckpointScore(CheckpointType.SUSPENSION_SYSTEM, 8),
            CheckpointScore(CheckpointType.TIRES, 8),
            CheckpointScore(CheckpointType.LIGHTING_SYSTEM, 8),
            CheckpointScore(CheckpointType.GAS_EMISSIONS, 8),
            CheckpointScore(CheckpointType.ELECTRICAL_SYSTEM, 8),
            CheckpointScore(CheckpointType.BODY_STRUCTURE, 8)
        ]

        inspection.update_checkpoint_scores(safe_scores)
        safety_result = inspection.calculate_safety_result()

        assert safety_result.is_safe
        assert safety_result.total_score == 64
        assert safety_result.max_score == 80
        assert not safety_result.requires_reinspection

    def test_has_critical_failures(self):
        """Test critical failure detection."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        # Add scores with one critical failure
        scores_with_failure = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8),
            CheckpointScore(CheckpointType.TIRES, 4)  # Critical failure
        ]

        inspection.update_checkpoint_scores(scores_with_failure)
        assert inspection.has_critical_failures()

    def test_get_scores_by_checkpoint(self):
        """Test getting scores organized by checkpoint type."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        scores = [
            CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8, "Good"),
            CheckpointScore(CheckpointType.TIRES, 7, "Fair")
        ]

        inspection.update_checkpoint_scores(scores)
        scores_dict = inspection.get_scores_by_checkpoint()

        assert len(scores_dict) == 2
        assert scores_dict[CheckpointType.BRAKING_SYSTEM].score == 8
        assert scores_dict[CheckpointType.TIRES].score == 7

    def test_equality_and_hashing(self):
        """Test equality and hashing based on inspection ID."""
        inspector_id = uuid4()
        inspection_id = uuid4()

        inspection1 = Inspection("ABC123", VehicleType.CAR, inspector_id, inspection_id)
        inspection2 = Inspection("XYZ789", VehicleType.MOTORCYCLE, inspector_id, inspection_id)
        inspection3 = Inspection("ABC123", VehicleType.CAR, inspector_id)

        assert inspection1 == inspection2  # Same ID
        assert inspection1 != inspection3  # Different ID
        assert hash(inspection1) == hash(inspection2)
        assert hash(inspection1) != hash(inspection3)

    def test_string_representations(self):
        """Test string representations."""
        inspection = Inspection("ABC123", VehicleType.CAR, uuid4())

        str_repr = str(inspection)
        assert "Inspection(" in str_repr
        assert "ABC123" in str_repr
        assert "draft" in str_repr

        repr_str = repr(inspection)
        assert "Inspection(id=" in repr_str
        assert "license_plate='ABC123'" in repr_str
        assert "vehicle_type=car" in repr_str
        assert "status=draft" in repr_str
