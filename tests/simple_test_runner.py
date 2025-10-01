"""Simple test runner for booking functionality without pytest."""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

# Add src to path
sys.path.insert(0, '/app')

from src.vehicle_inspection.domain.entities.booking import Booking, BookingStatus
from src.vehicle_inspection.domain.value_objects.time_slot import TimeSlot
from src.vehicle_inspection.infrastructure.repositories.simple_booking_service import InMemoryBookingService


def test_booking_entity():
    """Test booking entity functionality."""
    print("Testing Booking Entity...")

    user_id = uuid4()
    appointment_date = datetime.utcnow() + timedelta(days=1)

    # Test creation
    booking = Booking(
        license_plate="ABC123",
        appointment_date=appointment_date,
        user_id=user_id
    )

    assert booking.license_plate == "ABC123"
    assert booking.status == BookingStatus.PENDING
    assert booking.id is not None
    print("✓ Booking creation works")

    # Test confirmation
    booking.confirm()
    assert booking.status == BookingStatus.CONFIRMED
    print("✓ Booking confirmation works")

    # Test cancellation
    booking.cancel()
    assert booking.status == BookingStatus.CANCELLED
    print("✓ Booking cancellation works")

    print("✓ All booking entity tests passed!\n")


def test_time_slot():
    """Test time slot value object."""
    print("Testing TimeSlot Value Object...")

    from datetime import time

    slot_date = datetime(2025, 10, 1, 9, 0)
    start_time = time(9, 0)
    end_time = time(10, 0)

    # Test creation
    slot = TimeSlot(
        date=slot_date,
        start_time=start_time,
        end_time=end_time
    )

    assert slot.is_available is True
    assert slot.available_spots == 1
    assert slot.format_time_range() == "09:00 - 10:00"
    print("✓ TimeSlot creation works")

    # Test with booking
    new_slot = slot.with_booking()
    assert new_slot.current_bookings == 1
    assert new_slot.is_available is False
    print("✓ TimeSlot booking works")

    # Test without booking
    empty_slot = new_slot.without_booking()
    assert empty_slot.current_bookings == 0
    assert empty_slot.is_available is True
    print("✓ TimeSlot booking removal works")

    print("✓ All time slot tests passed!\n")


async def test_booking_service():
    """Test booking service functionality."""
    print("Testing Booking Service...")

    service = InMemoryBookingService()

    # Test available slots
    from datetime import date
    target_date = date.today() + timedelta(days=1)
    slots = await service.get_available_slots(target_date)

    assert len(slots) > 0
    assert all(slot.is_available for slot in slots)
    print("✓ Available slots retrieval works")

    # Test booking creation
    user_id = service.get_test_user_id()
    appointment_date = datetime.combine(target_date, datetime.min.time().replace(hour=10))

    booking = await service.create_booking("ABC123", appointment_date, user_id)
    assert booking.license_plate == "ABC123"
    assert booking.status == "pending"
    print("✓ Booking creation works")

    # Test booking confirmation
    confirmed_booking = await service.confirm_booking(booking.id, user_id)
    assert confirmed_booking.status == "confirmed"
    print("✓ Booking confirmation works")

    # Test slot becomes unavailable
    slots_after = await service.get_available_slots(target_date)
    slot_10am = next((s for s in slots_after if s.start_time.hour == 10), None)
    assert slot_10am is not None
    assert slot_10am.is_available is False
    print("✓ Slot availability tracking works")

    # Test duplicate booking prevention
    try:
        await service.create_booking("XYZ789", appointment_date, user_id)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Time slot is not available" in str(e)
        print("✓ Duplicate booking prevention works")

    print("✓ All booking service tests passed!\n")


def run_tests():
    """Run all tests."""
    print("Running Booking Feature Tests\n")
    print("=" * 50)

    try:
        # Unit tests
        test_booking_entity()
        test_time_slot()

        # Integration tests
        asyncio.run(test_booking_service())

        print("=" * 50)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("The booking functionality is working correctly.")

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
