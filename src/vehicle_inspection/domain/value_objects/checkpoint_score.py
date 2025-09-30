"""Checkpoint score value object."""

from dataclasses import dataclass
from .checkpoint_types import CheckpointType


@dataclass(frozen=True)
class CheckpointScore:
    """Immutable value object representing a single checkpoint score."""

    checkpoint_type: CheckpointType
    score: int
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate checkpoint score data."""
        if not isinstance(self.score, int):
            raise ValueError("Score must be an integer")
        if not (1 <= self.score <= 10):
            raise ValueError("Score must be between 1 and 10 inclusive")
        if not isinstance(self.checkpoint_type, CheckpointType):
            raise ValueError("checkpoint_type must be a CheckpointType enum")

    @property
    def is_critical_failure(self) -> bool:
        """Check if this score represents a critical failure."""
        return self.score < 5

    @property
    def is_excellent(self) -> bool:
        """Check if this score represents excellent condition."""
        return self.score >= 9

    @property
    def performance_level(self) -> str:
        """Get human-readable performance level."""
        if self.score >= 9:
            return "EXCELLENT"
        elif self.score >= 7:
            return "GOOD"
        elif self.score >= 5:
            return "ACCEPTABLE"
        elif self.score >= 3:
            return "POOR"
        else:
            return "CRITICAL"
