"""Simple in-memory repositories for development."""

from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict
from uuid import UUID, uuid4


class SimpleBooking:
    """Simple booking data class."""

    def __init__(
        self,
        license_plate: str,
        appointment_date: datetime,
        user_id: UUID,
        booking_id: Optional[UUID] = None,
        status: str = "pending"
    ):
        self.id = booking_id or uuid4()
        self.license_plate = license_plate
        self.appointment_date = appointment_date
        self.user_id = user_id
        self.status = status
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def confirm(self) -> None:
        """Confirm the booking."""
        if self.status != "pending":
            raise ValueError("Only pending bookings can be confirmed")
        self.status = "confirmed"
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel the booking."""
        if self.status in ["completed", "cancelled"]:
            raise ValueError("Cannot cancel completed or already cancelled bookings")
        self.status = "cancelled"
        self.updated_at = datetime.utcnow()


class SimpleTimeSlot:
    """Simple time slot data class."""

    def __init__(
        self,
        date: datetime,
        start_time: time,
        end_time: time,
        is_available: bool = True,
        max_bookings: int = 1,
        current_bookings: int = 0
    ):
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.is_available = is_available
        self.max_bookings = max_bookings
        self.current_bookings = current_bookings

    @property
    def available_spots(self) -> int:
        """Get number of available spots."""
        return self.max_bookings - self.current_bookings

    @property
    def time_range(self) -> str:
        """Get formatted time range."""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"


class InMemoryBookingService:
    """Simple in-memory booking service for development."""

    def __init__(self):
        self._bookings: Dict[UUID, SimpleBooking] = {}
        self._users: Dict[UUID, dict] = {}
        self._vehicles: Dict[str, dict] = {}
        self._create_test_data()

    def _create_test_data(self):
        """Create test users and vehicles."""
        # Test users
        test_user_id = uuid4()
        self._users[test_user_id] = {
            "id": test_user_id,
            "email": "testuser@example.com",
            "role": "owner"
        }

        # Test vehicles
        test_plates = ["ABC123", "XYZ789", "DEF456"]
        for plate in test_plates:
            self._vehicles[plate] = {
                "license_plate": plate,
                "make": "TestMake",
                "model": "TestModel",
                "year": 2020,
                "vehicle_type": "car"
            }

    def get_test_user_id(self) -> UUID:
        """Get test user ID."""
        return next(iter(self._users.keys()))

    async def create_booking(
        self,
        license_plate: str,
        appointment_date: datetime,
        user_id: UUID
    ) -> SimpleBooking:
        """Create a new booking."""
        # Validate inputs
        if not license_plate or not license_plate.strip():
            raise ValueError("License plate is required")

        if appointment_date <= datetime.utcnow():
            raise ValueError("Appointment must be in the future")

        if user_id not in self._users:
            raise ValueError("User not found")

        # Normalize license plate
        normalized_plate = license_plate.strip().upper()

        # Check if slot is available
        if not await self.is_slot_available(appointment_date):
            raise ValueError("Time slot is not available")

        # Create booking
        booking = SimpleBooking(
            license_plate=normalized_plate,
            appointment_date=appointment_date,
            user_id=user_id
        )

        # Store booking
        self._bookings[booking.id] = booking

        # Add vehicle if it doesn't exist
        if normalized_plate not in self._vehicles:
            self._vehicles[normalized_plate] = {
                "license_plate": normalized_plate,
                "make": "Unknown",
                "model": "Unknown",
                "year": 2020,
                "vehicle_type": "car"
            }

        return booking

    async def get_booking(self, booking_id: UUID) -> Optional[SimpleBooking]:
        """Get booking by ID."""
        return self._bookings.get(booking_id)

    async def get_user_bookings(self, user_id: UUID) -> List[SimpleBooking]:
        """Get all bookings for a user."""
        return [booking for booking in self._bookings.values()
                if booking.user_id == user_id]

    async def confirm_booking(self, booking_id: UUID, user_id: UUID) -> SimpleBooking:
        """Confirm a booking."""
        booking = self._bookings.get(booking_id)
        if not booking:
            raise ValueError("Booking not found")

        if booking.user_id != user_id:
            raise ValueError("You can only confirm your own bookings")

        booking.confirm()
        return booking

    async def cancel_booking(self, booking_id: UUID, user_id: UUID) -> SimpleBooking:
        """Cancel a booking."""
        booking = self._bookings.get(booking_id)
        if not booking:
            raise ValueError("Booking not found")

        if booking.user_id != user_id:
            raise ValueError("You can only cancel your own bookings")

        booking.cancel()
        return booking

    async def get_available_slots(self, target_date: date) -> List[SimpleTimeSlot]:
        """Get available slots for a date."""
        slots = []

        # Generate hourly slots from 8 AM to 5 PM
        for hour in range(8, 17):
            start_time = time(hour, 0)
            end_time = time(hour + 1, 0) if hour < 16 else time(17, 0)

            # Count existing bookings for this slot
            slot_datetime = datetime.combine(target_date, start_time)
            booked_count = sum(1 for booking in self._bookings.values()
                             if (booking.appointment_date.date() == target_date and
                                 booking.appointment_date.time() == start_time and
                                 booking.status in ["pending", "confirmed"]))

            slot = SimpleTimeSlot(
                date=slot_datetime,
                start_time=start_time,
                end_time=end_time,
                is_available=booked_count == 0,
                max_bookings=1,
                current_bookings=booked_count
            )

            slots.append(slot)

        return slots

    async def is_slot_available(self, appointment_date: datetime) -> bool:
        """Check if a specific slot is available."""
        target_date = appointment_date.date()
        target_time = appointment_date.time()

        # Count bookings for this exact datetime
        booked_count = sum(1 for booking in self._bookings.values()
                         if (booking.appointment_date.date() == target_date and
                             booking.appointment_date.time() == target_time and
                             booking.status in ["pending", "confirmed"]))

        return booked_count == 0
