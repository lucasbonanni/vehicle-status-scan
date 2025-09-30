"""Safety result value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyResult:
    """Immutable value object representing inspection safety result."""

    is_safe: bool
    total_score: int
    max_score: int
    requires_reinspection: bool
    observation: str = ""

    def __post_init__(self) -> None:
        """Validate safety result data."""
        if self.total_score < 0:
            raise ValueError("Total score cannot be negative")
        if self.max_score < 0:
            raise ValueError("Max score cannot be negative")
        if self.total_score > self.max_score:
            raise ValueError("Total score cannot exceed maximum score")

    @property
    def score_percentage(self) -> float:
        """Calculate score as percentage."""
        if self.max_score == 0:
            return 0.0
        return (self.total_score / self.max_score) * 100

    @property
    def status(self) -> str:
        """Get human-readable status."""
        if self.is_safe:
            return "SAFE"
        elif self.requires_reinspection:
            return "REQUIRES_REINSPECTION"
        else:
            return "CONDITIONAL"
