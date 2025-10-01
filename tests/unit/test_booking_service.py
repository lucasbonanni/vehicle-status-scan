"""Unit tests for booking service application layer."""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.vehicle_inspection.application.services.booking_service import (
    BookingService,
    LicensePlateValidator,
    TimeSlotGenerator
)
from src.vehicle_inspection.domain.entities.booking import Booking, BookingStatus
from src.vehicle_inspection.domain.entities.vehicle import Car
from src.vehicle_inspection.domain.value_objects.time_slot import TimeSlot


class TestLicensePlateValidator:
    """Test cases for LicensePlateValidator."""

    def test_validate_valid_plates(self):
        """Test validation of valid license plates."""
        valid_plates = ["ABC123", "XYZ789", "DEF456", "A1B2C3"]

        for plate in valid_plates:
            assert LicensePlateValidator.validate(plate) is True

    def test_validate_invalid_plates(self):
        """Test validation of invalid license plates."""
        invalid_plates = ["", "  ", "AB", "ABCDEFGHI", "ABC@123", "123-ABC"]

        for plate in invalid_plates:
            assert LicensePlateValidator.validate(plate) is False

    def test_validate_none_plate(self):
        """Test validation of None license plate."""
        assert LicensePlateValidator.validate(None) is False

    def test_normalize_plate(self):
        """Test license plate normalization."""
        test_cases = [
            ("abc123", "ABC123"),
            ("  XYZ789  ", "XYZ789"),
            ("def456", "DEF456"),
            ("  abc 123  ", "ABC 123")
        ]

        for input_plate, expected in test_cases:
            assert LicensePlateValidator.normalize(input_plate) == expected


class TestTimeSlotGenerator:
    """Test cases for TimeSlotGenerator."""

    def test_default_generator_settings(self):
        """Test default time slot generator settings."""
        generator = TimeSlotGenerator()

        assert generator.start_hour == 8
        assert generator.end_hour == 17
        assert generator.slot_duration_minutes == 60

    def test_custom_generator_settings(self):
        """Test custom time slot generator settings."""
        generator = TimeSlotGenerator(start_hour=9, end_hour=18, slot_duration_minutes=30)

        assert generator.start_hour == 9
        assert generator.end_hour == 18
        assert generator.slot_duration_minutes == 30

    def test_generate_slots_default_settings(self):
        """Test slot generation with default settings."""
        generator = TimeSlotGenerator()
        target_date = date(2025, 10, 1)

        slots = generator.generate_slots_for_date(target_date)

        # Should generate 9 slots (8 AM to 5 PM, 1-hour slots)
        assert len(slots) == 9

        # Check first slot
        first_slot = slots[0]
        assert first_slot.start_time.hour == 8
        assert first_slot.start_time.minute == 0
        assert first_slot.end_time.hour == 9
        assert first_slot.end_time.minute == 0

        # Check last slot
        last_slot = slots[-1]
        assert last_slot.start_time.hour == 16
        assert last_slot.start_time.minute == 0
        assert last_slot.end_time.hour == 17
        assert last_slot.end_time.minute == 0

    def test_generate_slots_custom_settings(self):
        """Test slot generation with custom settings."""
        generator = TimeSlotGenerator(start_hour=10, end_hour=14, slot_duration_minutes=30)
        target_date = date(2025, 10, 1)

        slots = generator.generate_slots_for_date(target_date)

        # Should generate 8 slots (10 AM to 2 PM, 30-minute slots)
        assert len(slots) == 8

        # Check first slot
        first_slot = slots[0]
        assert first_slot.start_time.hour == 10
        assert first_slot.start_time.minute == 0
        assert first_slot.end_time.hour == 10
        assert first_slot.end_time.minute == 30

    def test_generate_slots_all_available(self):
        """Test that generated slots are all available initially."""
        generator = TimeSlotGenerator()
        target_date = date(2025, 10, 1)

        slots = generator.generate_slots_for_date(target_date)

        for slot in slots:
            assert slot.is_available is True
            assert slot.current_bookings == 0
            assert slot.max_bookings == 1


class TestBookingService:
    """Test cases for BookingService."""

    def setup_mocks(self):
        """Set up mock repositories for testing."""
        self.mock_booking_repo = AsyncMock()
        self.mock_vehicle_repo = AsyncMock()
        self.mock_user_repo = AsyncMock()
        self.mock_time_generator = Mock()

        self.service = BookingService(
            self.mock_booking_repo,
            self.mock_vehicle_repo,
            self.mock_user_repo,
            self.mock_time_generator
        )

    def test_service_initialization(self):
        """Test booking service initialization."""
        self.setup_mocks()

        assert self.service._booking_repository == self.mock_booking_repo
        assert self.service._vehicle_repository == self.mock_vehicle_repo
        assert self.service._user_repository == self.mock_user_repo
        assert self.service._time_slot_generator == self.mock_time_generator

    @pytest.mark.asyncio
    async def test_get_available_slots(self):
        """Test getting available slots."""
        self.setup_mocks()

        target_date = date(2025, 10, 1)
        mock_slots = [
            TimeSlot(
                date=datetime.combine(target_date, datetime.min.time()),
                start_time=datetime.min.time().replace(hour=9),
                end_time=datetime.min.time().replace(hour=10),
                is_available=True
            )
        ]

        self.mock_booking_repo.find_available_slots.return_value = mock_slots

        result = await self.service.get_available_slots(target_date)

        assert result == mock_slots
        self.mock_booking_repo.find_available_slots.assert_called_once_with(target_date)

    @pytest.mark.asyncio
    async def test_request_appointment_success(self):
        """Test successful appointment request."""
        self.setup_mocks()

        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        # Mock dependencies
        self.mock_user_repo.exists.return_value = True
        self.mock_booking_repo.is_slot_available.return_value = True
        self.mock_vehicle_repo.find_by_license_plate.return_value = None
        self.mock_vehicle_repo.save.return_value = Car("ABC123", "Unknown", "Unknown", 2020)

        mock_booking = Booking("ABC123", appointment_date, user_id)
        self.mock_booking_repo.save.return_value = mock_booking

        result = await self.service.request_appointment("abc123", appointment_date, user_id)

        assert result == mock_booking
        self.mock_user_repo.exists.assert_called_once_with(user_id)
        self.mock_booking_repo.is_slot_available.assert_called_once_with(appointment_date)
        self.mock_vehicle_repo.find_by_license_plate.assert_called_once_with("ABC123")
        self.mock_booking_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_appointment_invalid_license_plate(self):
        """Test appointment request with invalid license plate."""
        self.setup_mocks()

        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        with pytest.raises(ValueError, match="Invalid license plate format"):
            await self.service.request_appointment("", appointment_date, user_id)

    @pytest.mark.asyncio
    async def test_request_appointment_user_not_found(self):
        """Test appointment request with non-existent user."""
        self.setup_mocks()

        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        self.mock_user_repo.exists.return_value = False

        with pytest.raises(ValueError, match="User not found"):
            await self.service.request_appointment("ABC123", appointment_date, user_id)

    @pytest.mark.asyncio
    async def test_request_appointment_slot_not_available(self):
        """Test appointment request with unavailable slot."""
        self.setup_mocks()

        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        self.mock_user_repo.exists.return_value = True
        self.mock_booking_repo.is_slot_available.return_value = False

        with pytest.raises(ValueError, match="Selected time slot is not available"):
            await self.service.request_appointment("ABC123", appointment_date, user_id)

    @pytest.mark.asyncio
    async def test_request_appointment_past_date(self):
        """Test appointment request with past date."""
        self.setup_mocks()

        user_id = uuid4()
        appointment_date = datetime.utcnow() - timedelta(days=1)  # Past date

        with pytest.raises(ValueError, match="Appointment must be scheduled for a future date"):
            await self.service.request_appointment("ABC123", appointment_date, user_id)

    @pytest.mark.asyncio
    async def test_confirm_booking_success(self):
        """Test successful booking confirmation."""
        self.setup_mocks()

        user_id = uuid4()
        booking_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        mock_booking = Booking("ABC123", appointment_date, user_id, booking_id)
        self.mock_booking_repo.find_by_id.return_value = mock_booking
        self.mock_booking_repo.save.return_value = mock_booking

        result = await self.service.confirm_booking(booking_id, user_id)

        assert result.status == BookingStatus.CONFIRMED
        self.mock_booking_repo.find_by_id.assert_called_once_with(booking_id)
        self.mock_booking_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_booking_not_found(self):
        """Test booking confirmation with non-existent booking."""
        self.setup_mocks()

        user_id = uuid4()
        booking_id = uuid4()

        self.mock_booking_repo.find_by_id.return_value = None

        with pytest.raises(ValueError, match="Booking not found"):
            await self.service.confirm_booking(booking_id, user_id)

    @pytest.mark.asyncio
    async def test_confirm_booking_wrong_user(self):
        """Test booking confirmation by wrong user."""
        self.setup_mocks()

        user_id = uuid4()
        wrong_user_id = uuid4()
        booking_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        mock_booking = Booking("ABC123", appointment_date, user_id, booking_id)
        self.mock_booking_repo.find_by_id.return_value = mock_booking

        with pytest.raises(ValueError, match="You can only confirm your own bookings"):
            await self.service.confirm_booking(booking_id, wrong_user_id)

    @pytest.mark.asyncio
    async def test_cancel_booking_success(self):
        """Test successful booking cancellation."""
        self.setup_mocks()

        user_id = uuid4()
        booking_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        mock_booking = Booking("ABC123", appointment_date, user_id, booking_id)
        self.mock_booking_repo.find_by_id.return_value = mock_booking
        self.mock_booking_repo.save.return_value = mock_booking

        result = await self.service.cancel_booking(booking_id, user_id)

        assert result.status == BookingStatus.CANCELLED
        self.mock_booking_repo.find_by_id.assert_called_once_with(booking_id)
        self.mock_booking_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_bookings(self):
        """Test getting user bookings."""
        self.setup_mocks()

        user_id = uuid4()
        mock_bookings = [
            Booking("ABC123", datetime.utcnow() + timedelta(days=1), user_id),
            Booking("XYZ789", datetime.utcnow() + timedelta(days=2), user_id)
        ]

        self.mock_booking_repo.find_by_user_id.return_value = mock_bookings

        result = await self.service.get_user_bookings(user_id)

        assert result == mock_bookings
        self.mock_booking_repo.find_by_user_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_booking(self):
        """Test getting specific booking."""
        self.setup_mocks()

        booking_id = uuid4()
        user_id = uuid4()
        appointment_date = datetime.utcnow() + timedelta(days=1)

        mock_booking = Booking("ABC123", appointment_date, user_id, booking_id)
        self.mock_booking_repo.find_by_id.return_value = mock_booking

        result = await self.service.get_booking(booking_id)

        assert result == mock_booking
        self.mock_booking_repo.find_by_id.assert_called_once_with(booking_id)

    @pytest.mark.asyncio
    async def test_get_vehicle_bookings(self):
        """Test getting vehicle bookings."""
        self.setup_mocks()

        license_plate = "abc123"
        user_id = uuid4()
        mock_bookings = [
            Booking("ABC123", datetime.utcnow() + timedelta(days=1), user_id)
        ]

        self.mock_booking_repo.find_by_license_plate.return_value = mock_bookings

        result = await self.service.get_vehicle_bookings(license_plate)

        assert result == mock_bookings
        self.mock_booking_repo.find_by_license_plate.assert_called_once_with("ABC123")
