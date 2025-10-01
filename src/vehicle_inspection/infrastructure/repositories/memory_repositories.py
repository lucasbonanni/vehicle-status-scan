"""In-memory repository implementations for testing and development."""

from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from src.vehicle_inspection.application.ports.repositories import BookingRepository, VehicleRepository, UserRepository
    from src.vehicle_inspection.domain.entities.booking import Booking, BookingStatus
    from src.vehicle_inspection.domain.entities.vehicle import Vehicle
    from src.vehicle_inspection.domain.value_objects.time_slot import TimeSlot


class InMemoryBookingRepository(BookingRepository):
    """In-memory implementation of booking repository."""

    def __init__(self):
        self._bookings: Dict[UUID, Booking] = {}
        self._time_slot_generator = self._create_default_time_slots()

    def _create_default_time_slots(self) -> Dict[str, List[TimeSlot]]:
        """Create default time slots for testing."""
        slots = {}

        # Generate slots for next 30 days
        for i in range(30):
            target_date = date.today() + timedelta(days=i)
            date_key = target_date.isoformat()

            daily_slots = []
            # Create hourly slots from 8 AM to 5 PM
            for hour in range(8, 17):
                start_time = time(hour, 0)
                end_time = time(hour + 1, 0) if hour < 16 else time(17, 0)

                slot = TimeSlot(
                    date=datetime.combine(target_date, start_time),
                    start_time=start_time,
                    end_time=end_time,
                    is_available=True,
                    max_bookings=1,
                    current_bookings=0
                )
                daily_slots.append(slot)

            slots[date_key] = daily_slots

        return slots

    async def save(self, booking: Booking) -> Booking:
        """Save a booking."""
        self._bookings[booking.id] = booking
        return booking

    async def find_by_id(self, booking_id: UUID) -> Optional[Booking]:
        """Find booking by ID."""
        return self._bookings.get(booking_id)

    async def find_by_license_plate(self, license_plate: str) -> List[Booking]:
        """Find all bookings for a license plate."""
        return [booking for booking in self._bookings.values()
                if booking.license_plate == license_plate]

    async def find_by_user_id(self, user_id: UUID) -> List[Booking]:
        """Find all bookings for a user."""
        return [booking for booking in self._bookings.values()
                if booking.user_id == user_id]

    async def find_available_slots(self, target_date: date) -> List[TimeSlot]:
        """Find available time slots for a specific date."""
        date_key = target_date.isoformat()
        if date_key not in self._time_slot_generator:
            return []

        # Get base slots
        base_slots = self._time_slot_generator[date_key]

        # Count bookings for each slot
        available_slots = []
        for slot in base_slots:
            # Count bookings in this time slot
            booked_count = sum(1 for booking in self._bookings.values()
                             if (booking.appointment_date.date() == target_date and
                                 booking.appointment_date.time() == slot.start_time and
                                 booking.status in [BookingStatus.PENDING, BookingStatus.CONFIRMED]))

            # Update slot with current booking count
            updated_slot = TimeSlot(
                date=slot.date,
                start_time=slot.start_time,
                end_time=slot.end_time,
                is_available=booked_count < slot.max_bookings,
                max_bookings=slot.max_bookings,
                current_bookings=booked_count
            )

            available_slots.append(updated_slot)

        return available_slots

    async def is_slot_available(self, appointment_date: datetime) -> bool:
        """Check if a specific datetime slot is available."""
        target_date = appointment_date.date()
        target_time = appointment_date.time()

        # Get available slots for the date
        available_slots = await self.find_available_slots(target_date)

        # Check if the specific time slot is available
        for slot in available_slots:
            if slot.start_time == target_time and slot.is_available:
                return True

        return False

    async def delete(self, booking_id: UUID) -> bool:
        """Delete a booking."""
        if booking_id in self._bookings:
            del self._bookings[booking_id]
            return True
        return False


class InMemoryVehicleRepository(VehicleRepository):
    """In-memory implementation of vehicle repository."""

    def __init__(self):
        self._vehicles: Dict[str, Vehicle] = {}

    async def save(self, vehicle: Vehicle) -> Vehicle:
        """Save a vehicle."""
        self._vehicles[vehicle.license_plate] = vehicle
        return vehicle

    async def find_by_license_plate(self, license_plate: str) -> Optional[Vehicle]:
        """Find vehicle by license plate."""
        return self._vehicles.get(license_plate)

    async def find_all(self) -> List[Vehicle]:
        """Find all vehicles."""
        return list(self._vehicles.values())

    async def delete(self, license_plate: str) -> bool:
        """Delete a vehicle."""
        if license_plate in self._vehicles:
            del self._vehicles[license_plate]
            return True
        return False


class InMemoryUserRepository(UserRepository):
    """In-memory implementation of user repository."""

    def __init__(self):
        self._users: Dict[UUID, dict] = {}
        # Add some test users
        self._create_test_users()

    def _create_test_users(self):
        """Create some test users."""
        test_users = [
            {"id": uuid4(), "email": "user1@example.com", "role": "owner"},
            {"id": uuid4(), "email": "user2@example.com", "role": "owner"},
            {"id": uuid4(), "email": "inspector@example.com", "role": "inspector"},
        ]

        for user in test_users:
            self._users[user["id"]] = user

    async def find_by_id(self, user_id: UUID) -> Optional[dict]:
        """Find user by ID."""
        return self._users.get(user_id)

    async def exists(self, user_id: UUID) -> bool:
        """Check if user exists."""
        return user_id in self._users

    def get_test_user_id(self) -> UUID:
        """Get a test user ID for development."""
        return next(iter(self._users.keys()))
