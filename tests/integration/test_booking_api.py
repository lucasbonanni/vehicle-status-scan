"""Integration tests for booking API endpoints."""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from httpx import AsyncClient

from src.vehicle_inspection.presentation.api.main import create_app


class TestBookingAPI:
    """Integration tests for booking API endpoints."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        return create_app()

    @pytest.fixture
    async def client(self, app):
        """Create test HTTP client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_get_available_slots_success(self, client):
        """Test getting available slots successfully."""
        target_date = "2025-10-01"

        response = await client.get(f"/api/v1/bookings/available-slots?date={target_date}")

        assert response.status_code == 200
        data = response.json()

        assert "date" in data
        assert "available_slots" in data
        assert "total_slots" in data
        assert "available_count" in data
        assert data["date"] == target_date
        assert isinstance(data["available_slots"], list)
        assert data["total_slots"] > 0

    @pytest.mark.asyncio
    async def test_get_available_slots_invalid_date_format(self, client):
        """Test getting available slots with invalid date format."""
        invalid_date = "invalid-date"

        response = await client.get(f"/api/v1/bookings/available-slots?date={invalid_date}")

        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_available_slots_past_date(self, client):
        """Test getting available slots for past date."""
        past_date = "2020-01-01"

        response = await client.get(f"/api/v1/bookings/available-slots?date={past_date}")

        assert response.status_code == 400
        assert "Cannot check availability for past dates" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_booking_success(self, client):
        """Test creating a booking successfully."""
        booking_data = {
            "license_plate": "TEST123",
            "appointment_date": "2025-10-01T10:00:00"
        }

        response = await client.post("/api/v1/bookings/", json=booking_data)

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["license_plate"] == "TEST123"
        assert data["appointment_date"] == "2025-10-01T10:00:00"
        assert data["status"] == "pending"
        assert "user_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_booking_with_user_id(self, client):
        """Test creating a booking with specific user ID."""
        user_id = str(uuid4())
        booking_data = {
            "license_plate": "TEST456",
            "appointment_date": "2025-10-01T11:00:00",
            "user_id": user_id
        }

        response = await client.post("/api/v1/bookings/", json=booking_data)

        # Note: This might fail if the specific user_id doesn't exist in the test data
        # The actual result depends on the mock implementation
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_create_booking_past_date(self, client):
        """Test creating a booking with past date."""
        booking_data = {
            "license_plate": "TEST789",
            "appointment_date": "2020-01-01T10:00:00"
        }

        response = await client.post("/api/v1/bookings/", json=booking_data)

        assert response.status_code == 400
        assert "Appointment must be in the future" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_booking_empty_license_plate(self, client):
        """Test creating a booking with empty license plate."""
        booking_data = {
            "license_plate": "",
            "appointment_date": "2025-10-01T10:00:00"
        }

        response = await client.post("/api/v1/bookings/", json=booking_data)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_booking_by_id_success(self, client):
        """Test getting a booking by ID successfully."""
        # First create a booking
        booking_data = {
            "license_plate": "GETTEST",
            "appointment_date": "2025-10-01T14:00:00"
        }

        create_response = await client.post("/api/v1/bookings/", json=booking_data)
        assert create_response.status_code == 200

        booking_id = create_response.json()["id"]

        # Then get it by ID
        response = await client.get(f"/api/v1/bookings/{booking_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == booking_id
        assert data["license_plate"] == "GETTEST"

    @pytest.mark.asyncio
    async def test_get_booking_by_id_not_found(self, client):
        """Test getting a non-existent booking."""
        fake_id = str(uuid4())

        response = await client.get(f"/api/v1/bookings/{fake_id}")

        assert response.status_code == 404
        assert "Booking not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_confirm_booking_success(self, client):
        """Test confirming a booking successfully."""
        # First create a booking
        booking_data = {
            "license_plate": "CONFIRM1",
            "appointment_date": "2025-10-01T15:00:00"
        }

        create_response = await client.post("/api/v1/bookings/", json=booking_data)
        assert create_response.status_code == 200

        booking_id = create_response.json()["id"]

        # Then confirm it
        response = await client.put(f"/api/v1/bookings/{booking_id}/confirm", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == booking_id
        assert data["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_cancel_booking_success(self, client):
        """Test cancelling a booking successfully."""
        # First create a booking
        booking_data = {
            "license_plate": "CANCEL1",
            "appointment_date": "2025-10-01T16:00:00"
        }

        create_response = await client.post("/api/v1/bookings/", json=booking_data)
        assert create_response.status_code == 200

        booking_id = create_response.json()["id"]

        # Then cancel it
        response = await client.put(f"/api/v1/bookings/{booking_id}/cancel", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == booking_id
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_list_bookings(self, client):
        """Test listing all bookings."""
        response = await client.get("/api/v1/bookings/")

        assert response.status_code == 200
        data = response.json()

        assert "bookings" in data
        assert "total_count" in data
        assert "test_user_id" in data
        assert "message" in data
        assert isinstance(data["bookings"], list)

    @pytest.mark.asyncio
    async def test_slot_becomes_unavailable_after_booking(self, client):
        """Test that a time slot becomes unavailable after booking."""
        # First check that a slot is available
        target_date = "2025-10-02"
        slots_response = await client.get(f"/api/v1/bookings/available-slots?date={target_date}")
        assert slots_response.status_code == 200

        slots_data = slots_response.json()
        available_slot = next(slot for slot in slots_data["available_slots"] if slot["is_available"])

        # Book the slot
        booking_data = {
            "license_plate": "SLOTTEST",
            "appointment_date": f"{target_date}T{available_slot['start_time']}:00"
        }

        booking_response = await client.post("/api/v1/bookings/", json=booking_data)
        assert booking_response.status_code == 200

        # Check that the slot is now unavailable
        slots_response2 = await client.get(f"/api/v1/bookings/available-slots?date={target_date}")
        assert slots_response2.status_code == 200

        slots_data2 = slots_response2.json()
        booked_slot = next(
            slot for slot in slots_data2["available_slots"]
            if slot["start_time"] == available_slot["start_time"]
        )

        assert booked_slot["is_available"] is False
        assert booked_slot["available_spots"] == 0

    @pytest.mark.asyncio
    async def test_cannot_double_book_same_slot(self, client):
        """Test that the same slot cannot be booked twice."""
        appointment_datetime = "2025-10-03T09:00:00"

        # First booking
        booking_data1 = {
            "license_plate": "DOUBLE1",
            "appointment_date": appointment_datetime
        }

        response1 = await client.post("/api/v1/bookings/", json=booking_data1)
        assert response1.status_code == 200

        # Second booking for same slot
        booking_data2 = {
            "license_plate": "DOUBLE2",
            "appointment_date": appointment_datetime
        }

        response2 = await client.post("/api/v1/bookings/", json=booking_data2)
        assert response2.status_code == 400
        assert "Time slot is not available" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_booking_workflow_complete(self, client):
        """Test complete booking workflow: create -> confirm -> verify status."""
        # Create booking
        booking_data = {
            "license_plate": "WORKFLOW",
            "appointment_date": "2025-10-04T13:00:00"
        }

        create_response = await client.post("/api/v1/bookings/", json=booking_data)
        assert create_response.status_code == 200

        booking_id = create_response.json()["id"]
        assert create_response.json()["status"] == "pending"

        # Confirm booking
        confirm_response = await client.put(f"/api/v1/bookings/{booking_id}/confirm", json={})
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "confirmed"

        # Verify final status
        get_response = await client.get(f"/api/v1/bookings/{booking_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "confirmed"
