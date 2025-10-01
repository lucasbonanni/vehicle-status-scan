"""Time slot value object for appointment scheduling."""

from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class TimeSlot:
    """Immutable value object representing an available time slot."""

    date: datetime
    start_time: time
    end_time: time
    is_available: bool = True
    max_bookings: int = 1
    current_bookings: int = 0

    def __post_init__(self) -> None:
        """Validate time slot data."""
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time")
        if self.current_bookings < 0:
            raise ValueError("Current bookings cannot be negative")
        if self.max_bookings < 1:
            raise ValueError("Max bookings must be at least 1")
        if self.current_bookings > self.max_bookings:
            raise ValueError("Current bookings cannot exceed max bookings")

    @property
    def is_fully_booked(self) -> bool:
        """Check if time slot is fully booked."""
        return self.current_bookings >= self.max_bookings

    @property
    def available_spots(self) -> int:
        """Get number of available spots."""
        return self.max_bookings - self.current_bookings

    @property
    def datetime_start(self) -> datetime:
        """Get start datetime combining date and start_time."""
        return datetime.combine(self.date.date(), self.start_time)

    @property
    def datetime_end(self) -> datetime:
        """Get end datetime combining date and end_time."""
        return datetime.combine(self.date.date(), self.end_time)

    def with_booking(self) -> "TimeSlot":
        """Create a new TimeSlot with one additional booking."""
        if self.is_fully_booked:
            raise ValueError("Cannot book a fully booked time slot")

        return TimeSlot(
            date=self.date,
            start_time=self.start_time,
            end_time=self.end_time,
            is_available=self.current_bookings + 1 < self.max_bookings,
            max_bookings=self.max_bookings,
            current_bookings=self.current_bookings + 1
        )

    def without_booking(self) -> "TimeSlot":
        """Create a new TimeSlot with one less booking."""
        if self.current_bookings == 0:
            raise ValueError("Cannot remove booking from empty time slot")

        return TimeSlot(
            date=self.date,
            start_time=self.start_time,
            end_time=self.end_time,
            is_available=True,
            max_bookings=self.max_bookings,
            current_bookings=self.current_bookings - 1
        )

    def format_time_range(self) -> str:
        """Get formatted time range string."""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    @property
    def time_range(self) -> str:
        """Get formatted time range string as property."""
        return self.format_time_range()
