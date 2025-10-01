"""Booking service implementing use cases for appointment management."""

from datetime import datetime, date, time, timedelta
from typing import List, Optional
from uuid import UUID

from ..ports.repositories import BookingRepository, VehicleRepository, UserRepository
from ...domain.entities.booking import Booking, BookingStatus
from ...domain.entities.vehicle import Vehicle, Car, Motorcycle
from ...domain.value_objects.time_slot import TimeSlot


class LicensePlateValidator:
    """Service for validating license plates."""

    @staticmethod
    def validate(license_plate: str) -> bool:
        """Validate license plate format."""
        if not license_plate:
            return False

        # Remove whitespace and convert to uppercase
        plate = license_plate.strip().upper()

        # Basic validation - adjust regex as needed for your country's format
        import re
        # Example: ABC123, AB123CD, etc. - customize as needed
        pattern = r'^[A-Z0-9]{3,8}$'
        return bool(re.match(pattern, plate))

    @staticmethod
    def normalize(license_plate: str) -> str:
        """Normalize license plate format."""
        return license_plate.strip().upper()


class TimeSlotGenerator:
    """Service for generating available time slots."""

    def __init__(self, start_hour: int = 8, end_hour: int = 17, slot_duration_minutes: int = 60):
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.slot_duration_minutes = slot_duration_minutes

    def generate_slots_for_date(self, target_date: date) -> List[TimeSlot]:
        """Generate all possible time slots for a given date."""
        slots = []
        current_time = time(self.start_hour, 0)
        end_time = time(self.end_hour, 0)

        while current_time < end_time:
            # Calculate slot end time
            slot_end = datetime.combine(target_date, current_time) + timedelta(minutes=self.slot_duration_minutes)
            slot_end_time = slot_end.time()

            # Don't create slot if it extends beyond working hours
            if slot_end_time <= end_time:
                slot = TimeSlot(
                    date=datetime.combine(target_date, current_time),
                    start_time=current_time,
                    end_time=slot_end_time,
                    is_available=True,
                    max_bookings=1,
                    current_bookings=0
                )
                slots.append(slot)

            # Move to next slot
            next_datetime = datetime.combine(target_date, current_time) + timedelta(minutes=self.slot_duration_minutes)
            current_time = next_datetime.time()

        return slots


class BookingService:
    """Application service for booking management."""

    def __init__(
        self,
        booking_repository: BookingRepository,
        vehicle_repository: VehicleRepository,
        user_repository: UserRepository,
        time_slot_generator: Optional[TimeSlotGenerator] = None
    ):
        self._booking_repository = booking_repository
        self._vehicle_repository = vehicle_repository
        self._user_repository = user_repository
        self._time_slot_generator = time_slot_generator or TimeSlotGenerator()
        self._license_validator = LicensePlateValidator()

    async def get_available_slots(self, target_date: date) -> List[TimeSlot]:
        """Get available time slots for a specific date."""
        # Generate all possible slots for the date
        all_slots = self._time_slot_generator.generate_slots_for_date(target_date)

        # Get available slots from repository (which considers existing bookings)
        available_slots = await self._booking_repository.find_available_slots(target_date)

        return available_slots

    async def request_appointment(
        self,
        license_plate: str,
        appointment_date: datetime,
        user_id: UUID
    ) -> Booking:
        """Request an appointment for vehicle inspection."""
        # Validate license plate
        if not self._license_validator.validate(license_plate):
            raise ValueError(f"Invalid license plate format: {license_plate}")

        # Normalize license plate
        normalized_plate = self._license_validator.normalize(license_plate)

        # Check if user exists
        if not await self._user_repository.exists(user_id):
            raise ValueError(f"User not found: {user_id}")

        # Check if slot is available
        if not await self._booking_repository.is_slot_available(appointment_date):
            raise ValueError("Selected time slot is not available")

        # Check if appointment is in the future
        if appointment_date <= datetime.utcnow():
            raise ValueError("Appointment must be scheduled for a future date")

        # Get or create vehicle
        vehicle = await self._vehicle_repository.find_by_license_plate(normalized_plate)
        if not vehicle:
            # For now, create a basic Car - in a real system, this might be determined differently
            vehicle = Car(normalized_plate, "Unknown", "Unknown", 2020)
            await self._vehicle_repository.save(vehicle)

        # Create booking
        booking = Booking(
            license_plate=normalized_plate,
            appointment_date=appointment_date,
            user_id=user_id,
            status=BookingStatus.PENDING
        )

        # Save booking
        saved_booking = await self._booking_repository.save(booking)

        return saved_booking

    async def confirm_booking(self, booking_id: UUID, user_id: UUID) -> Booking:
        """Confirm a pending booking."""
        booking = await self._booking_repository.find_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking not found: {booking_id}")

        # Check if user owns this booking
        if booking.user_id != user_id:
            raise ValueError("You can only confirm your own bookings")

        # Confirm the booking
        booking.confirm()

        # Save updated booking
        return await self._booking_repository.save(booking)

    async def cancel_booking(self, booking_id: UUID, user_id: UUID) -> Booking:
        """Cancel a booking."""
        booking = await self._booking_repository.find_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking not found: {booking_id}")

        # Check if user owns this booking
        if booking.user_id != user_id:
            raise ValueError("You can only cancel your own bookings")

        # Cancel the booking
        booking.cancel()

        # Save updated booking
        return await self._booking_repository.save(booking)

    async def get_user_bookings(self, user_id: UUID) -> List[Booking]:
        """Get all bookings for a user."""
        return await self._booking_repository.find_by_user_id(user_id)

    async def get_booking(self, booking_id: UUID) -> Optional[Booking]:
        """Get a specific booking by ID."""
        return await self._booking_repository.find_by_id(booking_id)

    async def get_vehicle_bookings(self, license_plate: str) -> List[Booking]:
        """Get all bookings for a vehicle."""
        normalized_plate = self._license_validator.normalize(license_plate)
        return await self._booking_repository.find_by_license_plate(normalized_plate)
