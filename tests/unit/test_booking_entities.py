"""Unit tests for booking domain entities."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.vehicle_inspection.domain.entities.booking import Booking, BookingStatus


class TestBooking:
    """Test cases for Booking entity."""

    def test_booking_creation(self):
        """Test basic booking creation."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id
        )

        assert booking.license_plate == "ABC123"
        assert booking.appointment_date == appointment_date
        assert booking.user_id == user_id
        assert booking.status == BookingStatus.PENDING
        assert booking.id is not None
        assert booking.created_at is not None
        assert booking.updated_at is not None

    def test_booking_creation_with_custom_id_and_status(self):
        """Test booking creation with custom ID and status."""
        booking_id = uuid4()
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="XYZ789",
            appointment_date=appointment_date,
            user_id=user_id,
            booking_id=booking_id,
            status=BookingStatus.CONFIRMED
        )

        assert booking.id == booking_id
        assert booking.status == BookingStatus.CONFIRMED

    def test_confirm_booking_success(self):
        """Test successful booking confirmation."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id
        )

        original_updated_at = booking.updated_at

        # Wait a small amount to ensure timestamp changes
        import time
        time.sleep(0.001)

        booking.confirm()

        assert booking.status == BookingStatus.CONFIRMED
        assert booking.updated_at > original_updated_at

    def test_confirm_booking_failure_not_pending(self):
        """Test booking confirmation fails if not pending."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.CONFIRMED
        )

        with pytest.raises(ValueError, match="Only pending bookings can be confirmed"):
            booking.confirm()

    def test_cancel_booking_from_pending(self):
        """Test cancelling a pending booking."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id
        )

        booking.cancel()

        assert booking.status == BookingStatus.CANCELLED

    def test_cancel_booking_from_confirmed(self):
        """Test cancelling a confirmed booking."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.CONFIRMED
        )

        booking.cancel()

        assert booking.status == BookingStatus.CANCELLED

    def test_cancel_booking_failure_completed(self):
        """Test cancelling a completed booking fails."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.COMPLETED
        )

        with pytest.raises(ValueError, match="Cannot cancel completed or already cancelled bookings"):
            booking.cancel()

    def test_cancel_booking_failure_already_cancelled(self):
        """Test cancelling an already cancelled booking fails."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.CANCELLED
        )

        with pytest.raises(ValueError, match="Cannot cancel completed or already cancelled bookings"):
            booking.cancel()

    def test_complete_booking_success(self):
        """Test completing a confirmed booking."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.CONFIRMED
        )

        booking.complete()

        assert booking.status == BookingStatus.COMPLETED

    def test_complete_booking_failure_not_confirmed(self):
        """Test completing a non-confirmed booking fails."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id
        )

        with pytest.raises(ValueError, match="Only confirmed bookings can be completed"):
            booking.complete()

    def test_is_editable_pending(self):
        """Test pending booking is editable."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id
        )

        assert booking.is_editable() is True

    def test_is_editable_confirmed(self):
        """Test confirmed booking is editable."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.CONFIRMED
        )

        assert booking.is_editable() is True

    def test_is_not_editable_completed(self):
        """Test completed booking is not editable."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.COMPLETED
        )

        assert booking.is_editable() is False

    def test_is_not_editable_cancelled(self):
        """Test cancelled booking is not editable."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.CANCELLED
        )

        assert booking.is_editable() is False

    def test_booking_equality(self):
        """Test booking equality based on ID."""
        user_id = uuid4()
        booking_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking1 = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id,
            booking_id=booking_id
        )

        booking2 = Booking(
            license_plate="XYZ789",  # Different details
            appointment_date=appointment_date + timedelta(hours=1),
            user_id=uuid4(),
            booking_id=booking_id  # Same ID
        )

        assert booking1 == booking2
        assert hash(booking1) == hash(booking2)

    def test_booking_inequality(self):
        """Test booking inequality with different IDs."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking1 = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id
        )

        booking2 = Booking(
            license_plate="ABC123",  # Same details
            appointment_date=appointment_date,
            user_id=user_id
        )

        assert booking1 != booking2  # Different auto-generated IDs
        assert hash(booking1) != hash(booking2)

    def test_booking_string_representation(self):
        """Test booking string representation."""
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        booking = Booking(
            license_plate="ABC123",
            appointment_date=appointment_date,
            user_id=user_id
        )

        str_repr = str(booking)
        assert "Booking(" in str_repr
        assert "ABC123" in str_repr
        assert "pending" in str_repr
        assert str(booking.id) in str_repr


class TestBookingStatus:
    """Test cases for BookingStatus enum."""

    def test_booking_status_values(self):
        """Test all booking status enum values."""
        assert BookingStatus.PENDING.value == "pending"
        assert BookingStatus.CONFIRMED.value == "confirmed"
        assert BookingStatus.COMPLETED.value == "completed"
        assert BookingStatus.CANCELLED.value == "cancelled"

    def test_booking_status_membership(self):
        """Test booking status enum membership."""
        assert BookingStatus.PENDING in BookingStatus
        assert BookingStatus.CONFIRMED in BookingStatus
        assert BookingStatus.COMPLETED in BookingStatus
        assert BookingStatus.CANCELLED in BookingStatus
