"""Unit tests for vehicle entities."""

import pytest
from src.vehicle_inspection.domain.entities.vehicle import Car, Motorcycle, VehicleType
from src.vehicle_inspection.domain.value_objects.checkpoint_types import CheckpointType
from src.vehicle_inspection.domain.value_objects.checkpoint_score import CheckpointScore


class TestCar:
    """Test cases for Car entity."""

    def test_car_creation(self):
        """Test basic car creation."""
        car = Car("ABC123", "Toyota", "Camry", 2020)

        assert car.license_plate == "ABC123"
        assert car.make == "Toyota"
        assert car.model == "Camry"
        assert car.year == 2020
        assert car.get_vehicle_type() == VehicleType.CAR

    def test_car_required_checkpoints(self):
        """Test car returns correct checkpoints."""
        car = Car("ABC123", "Toyota", "Camry", 2020)
        checkpoints = car.get_required_checkpoints()

        assert len(checkpoints) == 8
        assert CheckpointType.BRAKING_SYSTEM in checkpoints
        assert CheckpointType.TIRES in checkpoints
        assert CheckpointType.LIGHTING_SYSTEM in checkpoints

    def test_car_safety_calculation_pass(self):
        """Test car passes safety with good scores."""
        car = Car("ABC123", "Toyota", "Camry", 2020)

        # Create scores that should pass (all 8s = 64 points, >= 64 threshold)
        scores = [
            CheckpointScore(checkpoint_type, 8)
            for checkpoint_type in car.get_required_checkpoints()
        ]

        safety_result = car.calculate_safety(scores)

        assert safety_result.is_safe is True
        assert safety_result.total_score == 64
        assert safety_result.requires_reinspection is False
        assert safety_result.observation == ""

    def test_car_safety_calculation_fail_low_total(self):
        """Test car fails safety with low total score."""
        car = Car("ABC123", "Toyota", "Camry", 2020)

        # Create scores that result in low total (all 3s = 24 points, < 32 threshold)
        scores = [
            CheckpointScore(checkpoint_type, 3)
            for checkpoint_type in car.get_required_checkpoints()
        ]

        safety_result = car.calculate_safety(scores)

        assert safety_result.is_safe is False
        assert safety_result.total_score == 24
        assert safety_result.requires_reinspection is True
        assert "Total score too low" in safety_result.observation

    def test_car_safety_calculation_fail_critical_failure(self):
        """Test car fails safety with critical individual failure."""
        car = Car("ABC123", "Toyota", "Camry", 2020)

        # Create mostly good scores but one critical failure
        checkpoints = car.get_required_checkpoints()
        scores = [CheckpointScore(checkpoints[0], 4)]  # Critical failure in braking
        scores.extend([
            CheckpointScore(checkpoint_type, 8)
            for checkpoint_type in checkpoints[1:]
        ])

        safety_result = car.calculate_safety(scores)

        assert safety_result.is_safe is False
        assert safety_result.total_score == 60  # 4 + 7*8 = 60
        assert safety_result.requires_reinspection is True
        assert "Critical failures" in safety_result.observation


class TestMotorcycle:
    """Test cases for Motorcycle entity."""

    def test_motorcycle_creation(self):
        """Test basic motorcycle creation."""
        motorcycle = Motorcycle("XYZ789", "Harley", "Sportster", 2019)

        assert motorcycle.license_plate == "XYZ789"
        assert motorcycle.make == "Harley"
        assert motorcycle.model == "Sportster"
        assert motorcycle.year == 2019
        assert motorcycle.get_vehicle_type() == VehicleType.MOTORCYCLE

    def test_motorcycle_required_checkpoints(self):
        """Test motorcycle returns correct checkpoints."""
        motorcycle = Motorcycle("XYZ789", "Harley", "Sportster", 2019)
        checkpoints = motorcycle.get_required_checkpoints()

        assert len(checkpoints) == 8
        assert CheckpointType.BRAKING_SYSTEM in checkpoints
        assert CheckpointType.TIRES in checkpoints
        assert CheckpointType.LIGHTING_SYSTEM in checkpoints


class TestVehiclePolymorphism:
    """Test vehicle polymorphism and LSP compliance."""

    def test_vehicles_interchangeable(self):
        """Test that Car and Motorcycle can be used interchangeably."""
        vehicles = [
            Car("CAR123", "Toyota", "Camry", 2020),
            Motorcycle("BIKE456", "Harley", "Sportster", 2019)
        ]

        for vehicle in vehicles:
            # All vehicles should have these common behaviors
            assert len(vehicle.get_required_checkpoints()) == 8
            assert vehicle.get_vehicle_type() in [VehicleType.CAR, VehicleType.MOTORCYCLE]

            # Test safety calculation works for both
            good_scores = [
                CheckpointScore(checkpoint_type, 8)
                for checkpoint_type in vehicle.get_required_checkpoints()
            ]
            safety_result = vehicle.calculate_safety(good_scores)
            assert safety_result.total_score == 64

    def test_vehicle_equality(self):
        """Test vehicle equality based on license plate."""
        car1 = Car("ABC123", "Toyota", "Camry", 2020)
        car2 = Car("ABC123", "Honda", "Civic", 2021)  # Same license, different details
        motorcycle = Motorcycle("ABC123", "Harley", "Sportster", 2019)  # Same license

        assert car1 == car2  # Same license plate
        assert car1 == motorcycle  # Same license plate, different type
        assert hash(car1) == hash(car2)  # Same hash
