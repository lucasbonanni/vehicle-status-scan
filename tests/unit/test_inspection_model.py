"""Unit tests for InspectionModel database model."""

import json
import pytest
from datetime import datetime
from uuid import uuid4

from src.vehicle_inspection.infrastructure.database.models import InspectionModel
from src.vehicle_inspection.domain.entities.inspection import InspectionStatus
from src.vehicle_inspection.domain.entities.vehicle import VehicleType


class TestInspectionModel:
    """Test cases for InspectionModel."""

    def test_inspection_model_creation_with_required_fields(self):
        """Test creating InspectionModel with only required fields."""
        inspector_id = uuid4()

        model = InspectionModel(
            license_plate="ABC123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id
        )

        assert model.license_plate == "ABC123"
        assert model.vehicle_type == VehicleType.CAR
        assert model.inspector_id == inspector_id
        # SQLAlchemy defaults are applied during database insertion, not object creation
        assert model.status is None  # Will be set to DRAFT during DB insert
        assert model.observations is None  # Will be set to "" during DB insert
        assert model.checkpoint_scores is None
        assert model.total_score is None
        assert model.is_safe is None
        assert model.requires_reinspection is None

    def test_inspection_model_creation_with_all_fields(self):
        """Test creating InspectionModel with all fields."""
        inspector_id = uuid4()
        checkpoint_scores_data = [
            {"checkpoint_type": "braking", "score": 8, "notes": "Good condition"},
            {"checkpoint_type": "steering", "score": 9, "notes": "Excellent"}
        ]

        model = InspectionModel(
            license_plate="XYZ789",
            vehicle_type=VehicleType.MOTORCYCLE,
            inspector_id=inspector_id,
            checkpoint_scores=json.dumps(checkpoint_scores_data),
            total_score=85.5,
            is_safe=True,
            requires_reinspection=False,
            observations="Vehicle in excellent condition",
            status=InspectionStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )

        assert model.license_plate == "XYZ789"
        assert model.vehicle_type == VehicleType.MOTORCYCLE
        assert model.inspector_id == inspector_id
        assert model.checkpoint_scores == json.dumps(checkpoint_scores_data)
        assert model.total_score == 85.5
        assert model.is_safe is True
        assert model.requires_reinspection is False
        assert model.observations == "Vehicle in excellent condition"
        assert model.status == InspectionStatus.COMPLETED
        assert model.completed_at is not None

    def test_inspection_model_json_checkpoint_scores(self):
        """Test JSON serialization/deserialization of checkpoint scores."""
        inspector_id = uuid4()
        checkpoint_scores_data = [
            {"checkpoint_type": "braking", "score": 7, "notes": "Minor wear"},
            {"checkpoint_type": "steering", "score": 8, "notes": "Good"},
            {"checkpoint_type": "suspension", "score": 6, "notes": "Needs attention"}
        ]

        model = InspectionModel(
            license_plate="TEST123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id,
            checkpoint_scores=json.dumps(checkpoint_scores_data)
        )

        # Test that we can deserialize the JSON back
        stored_scores = json.loads(model.checkpoint_scores)
        assert len(stored_scores) == 3
        assert stored_scores[0]["checkpoint_type"] == "braking"
        assert stored_scores[0]["score"] == 7
        assert stored_scores[0]["notes"] == "Minor wear"

    def test_inspection_model_vehicle_type_enum(self):
        """Test VehicleType enum handling."""
        inspector_id = uuid4()

        # Test CAR
        car_model = InspectionModel(
            license_plate="CAR123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id
        )
        assert car_model.vehicle_type == VehicleType.CAR

        # Test MOTORCYCLE
        motorcycle_model = InspectionModel(
            license_plate="BIKE456",
            vehicle_type=VehicleType.MOTORCYCLE,
            inspector_id=inspector_id
        )
        assert motorcycle_model.vehicle_type == VehicleType.MOTORCYCLE

    def test_inspection_model_status_enum(self):
        """Test InspectionStatus enum handling."""
        inspector_id = uuid4()

        # Test DRAFT (default)
        draft_model = InspectionModel(
            license_plate="DRAFT123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id
        )
        assert draft_model.status == InspectionStatus.DRAFT

        # Test COMPLETED
        completed_model = InspectionModel(
            license_plate="DONE456",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id,
            status=InspectionStatus.COMPLETED
        )
        assert completed_model.status == InspectionStatus.COMPLETED

    def test_inspection_model_repr(self):
        """Test string representation of InspectionModel."""
        inspector_id = uuid4()

        model = InspectionModel(
            license_plate="REPR123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id,
            status=InspectionStatus.COMPLETED
        )

        repr_str = repr(model)
        assert "InspectionModel" in repr_str
        assert "REPR123" in repr_str
        assert "InspectionStatus.COMPLETED" in repr_str
        assert str(inspector_id) in repr_str

    def test_inspection_model_safety_metrics(self):
        """Test safety calculation fields."""
        inspector_id = uuid4()

        model = InspectionModel(
            license_plate="SAFE123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id,
            total_score=85.0,
            is_safe=True,
            requires_reinspection=False
        )

        assert model.total_score == 85.0
        assert model.is_safe is True
        assert model.requires_reinspection is False

    def test_inspection_model_with_unsafe_vehicle(self):
        """Test model with unsafe vehicle requiring reinspection."""
        inspector_id = uuid4()

        model = InspectionModel(
            license_plate="UNSAFE123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id,
            total_score=35.0,  # Below safety threshold
            is_safe=False,
            requires_reinspection=True,
            observations="Multiple critical failures detected"
        )

        assert model.total_score == 35.0
        assert model.is_safe is False
        assert model.requires_reinspection is True
        assert "critical failures" in model.observations

    def test_inspection_model_tablename(self):
        """Test that the table name is correctly set."""
        assert InspectionModel.__tablename__ == "inspections"

    def test_inspection_model_columns_exist(self):
        """Test that all expected columns exist in the model."""
        expected_columns = {
            'id', 'license_plate', 'vehicle_type', 'inspector_id',
            'checkpoint_scores', 'total_score', 'is_safe', 'requires_reinspection',
            'observations', 'status', 'created_at', 'updated_at', 'completed_at'
        }

        actual_columns = {col.name for col in InspectionModel.__table__.columns}

        assert expected_columns == actual_columns

    def test_inspection_model_database_defaults(self):
        """Test that database defaults are properly configured."""
        status_column = InspectionModel.__table__.columns['status']
        obs_column = InspectionModel.__table__.columns['observations']

        # Check that defaults are configured
        assert status_column.default is not None
        assert status_column.default.arg == InspectionStatus.DRAFT
        assert obs_column.default is not None
        assert obs_column.default.arg == ""

        # Check nullability
        assert not obs_column.nullable  # observations is NOT NULL with default ""
        assert not status_column.nullable  # status is NOT NULL with default DRAFT

    def test_inspection_model_explicit_values(self):
        """Test creating InspectionModel with explicit status and observations."""
        inspector_id = uuid4()

        model = InspectionModel(
            license_plate="EXPLICIT123",
            vehicle_type=VehicleType.CAR,
            inspector_id=inspector_id,
            status=InspectionStatus.COMPLETED,
            observations="Test observations"
        )

        assert model.status == InspectionStatus.COMPLETED
        assert model.observations == "Test observations"
