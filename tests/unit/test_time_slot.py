"""Unit tests for time slot value object."""

import pytest
from datetime import datetime, time, date

from src.vehicle_inspection.domain.value_objects.time_slot import TimeSlot


class TestTimeSlot:
    """Test cases for TimeSlot value object."""

    def test_time_slot_creation(self):
        """Test basic time slot creation."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time
        )

        assert slot.date == slot_date
        assert slot.start_time == start_time
        assert slot.end_time == end_time
        assert slot.is_available is True
        assert slot.max_bookings == 1
        assert slot.current_bookings == 0

    def test_time_slot_creation_with_custom_params(self):
        """Test time slot creation with custom parameters."""
        slot_date = datetime(2025, 10, 1, 14, 0)
        start_time = time(14, 0)
        end_time = time(15, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            is_available=False,
            max_bookings=2,
            current_bookings=1
        )

        assert slot.is_available is False
        assert slot.max_bookings == 2
        assert slot.current_bookings == 1

    def test_time_slot_validation_start_after_end(self):
        """Test time slot validation fails when start time is after end time."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(10, 0)
        end_time = time(9, 0)  # End before start

        with pytest.raises(ValueError, match="Start time must be before end time"):
            TimeSlot(
                date=slot_date,
                start_time=start_time,
                end_time=end_time
            )

    def test_time_slot_validation_start_equals_end(self):
        """Test time slot validation fails when start time equals end time."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(9, 0)  # Same as start

        with pytest.raises(ValueError, match="Start time must be before end time"):
            TimeSlot(
                date=slot_date,
                start_time=start_time,
                end_time=end_time
            )

    def test_time_slot_validation_negative_current_bookings(self):
        """Test time slot validation fails with negative current bookings."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        with pytest.raises(ValueError, match="Current bookings cannot be negative"):
            TimeSlot(
                date=slot_date,
                start_time=start_time,
                end_time=end_time,
                current_bookings=-1
            )

    def test_time_slot_validation_zero_max_bookings(self):
        """Test time slot validation fails with zero max bookings."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        with pytest.raises(ValueError, match="Max bookings must be at least 1"):
            TimeSlot(
                date=slot_date,
                start_time=start_time,
                end_time=end_time,
                max_bookings=0
            )

    def test_time_slot_validation_current_exceeds_max(self):
        """Test time slot validation fails when current bookings exceed max."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        with pytest.raises(ValueError, match="Current bookings cannot exceed max bookings"):
            TimeSlot(
                date=slot_date,
                start_time=start_time,
                end_time=end_time,
                max_bookings=2,
                current_bookings=3
            )

    def test_is_fully_booked_false(self):
        """Test is_fully_booked returns false when spots available."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            max_bookings=2,
            current_bookings=1
        )

        assert slot.is_fully_booked is False

    def test_is_fully_booked_true(self):
        """Test is_fully_booked returns true when no spots available."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            max_bookings=2,
            current_bookings=2
        )

        assert slot.is_fully_booked is True

    def test_available_spots(self):
        """Test available_spots calculation."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            max_bookings=3,
            current_bookings=1
        )

        assert slot.available_spots == 2

    def test_available_spots_zero(self):
        """Test available_spots returns zero when fully booked."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            max_bookings=1,
            current_bookings=1
        )

        assert slot.available_spots == 0

    def test_datetime_start(self):
        """Test datetime_start property."""
        target_date = date(2025, 10, 1)
        slot_date = datetime.combine(target_date, time(9, 0))
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time
        )

        expected_datetime = datetime(2025, 10, 1, 9, 0)
        assert slot.datetime_start == expected_datetime

    def test_datetime_end(self):
        """Test datetime_end property."""
        target_date = date(2025, 10, 1)
        slot_date = datetime.combine(target_date, time(9, 0))
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time
        )

        expected_datetime = datetime(2025, 10, 1, 10, 0)
        assert slot.datetime_end == expected_datetime

    def test_with_booking_success(self):
        """Test with_booking creates new slot with incremented booking count."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        original_slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            max_bookings=2,
            current_bookings=0
        )

        new_slot = original_slot.with_booking()

        # Original slot unchanged
        assert original_slot.current_bookings == 0
        assert original_slot.is_available is True

        # New slot has updated bookings
        assert new_slot.current_bookings == 1
        assert new_slot.is_available is True  # Still available (1 < 2)
        assert new_slot.max_bookings == 2

    def test_with_booking_becomes_unavailable(self):
        """Test with_booking makes slot unavailable when reaching max capacity."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        original_slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            max_bookings=1,
            current_bookings=0
        )

        new_slot = original_slot.with_booking()

        assert new_slot.current_bookings == 1
        assert new_slot.is_available is False  # Now unavailable (1 >= 1)

    def test_with_booking_failure_fully_booked(self):
        """Test with_booking fails when slot is fully booked."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            max_bookings=1,
            current_bookings=1
        )

        with pytest.raises(ValueError, match="Cannot book a fully booked time slot"):
            slot.with_booking()

    def test_without_booking_success(self):
        """Test without_booking creates new slot with decremented booking count."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        original_slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            max_bookings=2,
            current_bookings=2,
            is_available=False
        )

        new_slot = original_slot.without_booking()

        # Original slot unchanged
        assert original_slot.current_bookings == 2
        assert original_slot.is_available is False

        # New slot has updated bookings
        assert new_slot.current_bookings == 1
        assert new_slot.is_available is True  # Now available again

    def test_without_booking_failure_empty(self):
        """Test without_booking fails when slot has no bookings."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            current_bookings=0
        )

        with pytest.raises(ValueError, match="Cannot remove booking from empty time slot"):
            slot.without_booking()

    def test_format_time_range(self):
        """Test format_time_range returns properly formatted string."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 30)
        end_time = time(10, 45)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time
        )

        assert slot.format_time_range() == "09:30 - 10:45"

    def test_format_time_range_midnight(self):
        """Test format_time_range with midnight times."""
        slot_date = datetime(2025, 10, 1, 0, 0)
        start_time = time(0, 0)
        end_time = time(1, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time
        )

        assert slot.format_time_range() == "00:00 - 01:00"

    def test_time_slot_immutability(self):
        """Test that TimeSlot is immutable (dataclass frozen=True)."""
        slot_date = datetime(2025, 10, 1, 9, 0)
        start_time = time(9, 0)
        end_time = time(10, 0)

        slot = TimeSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time
        )

        # Attempting to modify should raise an error
        with pytest.raises(AttributeError):
            slot.current_bookings = 5

        with pytest.raises(AttributeError):
            slot.is_available = False
