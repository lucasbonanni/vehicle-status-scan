"""Checkpoint types enumeration."""

from enum import Enum


class CheckpointType(Enum):
    """Enumeration of inspection checkpoint types."""

    BRAKING_SYSTEM = "braking_system"
    STEERING_SYSTEM = "steering_system"
    SUSPENSION_SYSTEM = "suspension_system"
    TIRES = "tires"
    LIGHTING_SYSTEM = "lighting_system"
    GAS_EMISSIONS = "gas_emissions"
    ELECTRICAL_SYSTEM = "electrical_system"
    BODY_STRUCTURE = "body_structure"

    def get_description(self) -> str:
        """Get human-readable description of checkpoint."""
        descriptions = {
            self.BRAKING_SYSTEM: "Brake pads, brake fluid, brake lines, parking brake",
            self.STEERING_SYSTEM: "Steering wheel play, power steering, alignment",
            self.SUSPENSION_SYSTEM: "Shock absorbers, springs, ball joints, wheel bearings",
            self.TIRES: "Tread depth, tire pressure, sidewall condition, wear patterns",
            self.LIGHTING_SYSTEM: "Headlights, taillights, brake lights, turn signals",
            self.GAS_EMISSIONS: "Exhaust system, catalytic converter, emission levels",
            self.ELECTRICAL_SYSTEM: "Battery, alternator, starter, wiring, horn",
            self.BODY_STRUCTURE: "Frame integrity, doors, windows, mirrors, seatbelts",
        }
        return descriptions.get(self, "Unknown checkpoint")

    def is_applicable_to_vehicle_type(self, vehicle_type: str) -> bool:
        """Check if checkpoint applies to specific vehicle type."""
        # All current checkpoints apply to both cars and motorcycles
        # This can be extended if vehicle-specific checkpoints are needed
        return True
