"""SQLAlchemy repository implementations."""

from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.vehicle_inspection.application.ports.repositories import BookingRepository, VehicleRepository, UserRepository, InspectorRepository, AuthTokenRepository
from src.vehicle_inspection.domain.entities.booking import Booking, BookingStatus
from src.vehicle_inspection.domain.entities.vehicle import Vehicle, Car, Motorcycle
from src.vehicle_inspection.domain.entities.inspector import Inspector, InspectorRole, InspectorStatus
from src.vehicle_inspection.domain.value_objects.time_slot import TimeSlot
from src.vehicle_inspection.domain.value_objects.auth import AuthToken
from src.vehicle_inspection.infrastructure.database.models import BookingModel, TimeSlotModel, VehicleModel, UserModel, InspectorModel


class SQLAlchemyBookingRepository(BookingRepository):
    """SQLAlchemy implementation of booking repository."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, booking: Booking) -> Booking:
        """Save a booking to the database."""
        # Check if booking exists
        stmt = select(BookingModel).where(BookingModel.id == booking.id)
        result = await self._session.execute(stmt)
        existing_booking = result.scalar_one_or_none()

        if existing_booking:
            # Update existing booking
            existing_booking.license_plate = booking.license_plate
            existing_booking.appointment_date = booking.appointment_date
            existing_booking.status = booking.status
            existing_booking.user_id = booking.user_id
            existing_booking.updated_at = datetime.utcnow()
        else:
            # Create new booking
            booking_model = BookingModel(
                id=booking.id,
                license_plate=booking.license_plate,
                appointment_date=booking.appointment_date,
                status=booking.status,
                user_id=booking.user_id,
                created_at=booking.created_at,
                updated_at=datetime.utcnow()
            )
            self._session.add(booking_model)

        await self._session.flush()
        return booking

    async def find_by_id(self, booking_id: UUID) -> Optional[Booking]:
        """Find booking by ID."""
        stmt = select(BookingModel).where(BookingModel.id == booking_id)
        result = await self._session.execute(stmt)
        booking_model = result.scalar_one_or_none()

        if not booking_model:
            return None

        return self._model_to_entity(booking_model)

    async def find_by_license_plate(self, license_plate: str) -> List[Booking]:
        """Find all bookings for a license plate."""
        stmt = select(BookingModel).where(
            BookingModel.license_plate == license_plate.upper()
        ).order_by(BookingModel.appointment_date.desc())

        result = await self._session.execute(stmt)
        booking_models = result.scalars().all()

        return [self._model_to_entity(model) for model in booking_models]

    async def find_by_user_id(self, user_id: UUID) -> List[Booking]:
        """Find all bookings for a user."""
        stmt = select(BookingModel).where(
            BookingModel.user_id == user_id
        ).order_by(BookingModel.appointment_date.desc())

        result = await self._session.execute(stmt)
        booking_models = result.scalars().all()

        return [self._model_to_entity(model) for model in booking_models]

    async def find_available_slots(self, target_date: date) -> List[TimeSlot]:
        """Find available time slots for a specific date."""
        # First, try to get existing time slots from database
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)

        stmt = select(TimeSlotModel).where(
            and_(
                TimeSlotModel.date >= start_of_day,
                TimeSlotModel.date <= end_of_day,
                TimeSlotModel.is_available == True
            )
        ).order_by(TimeSlotModel.start_time)

        result = await self._session.execute(stmt)
        slot_models = result.scalars().all()

        if slot_models:
            # Return existing slots from database
            return [self._slot_model_to_value_object(model) for model in slot_models]
        else:
            # Generate default slots if none exist
            return self._generate_default_slots(target_date)

    async def is_slot_available(self, appointment_date: datetime) -> bool:
        """Check if a specific datetime slot is available."""
        # Check if there are any conflicting bookings
        stmt = select(func.count(BookingModel.id)).where(
            and_(
                BookingModel.appointment_date == appointment_date,
                BookingModel.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
            )
        )

        result = await self._session.execute(stmt)
        booking_count = result.scalar()

        # For now, assume max 1 booking per slot
        return booking_count < 1

    async def delete(self, booking_id: UUID) -> bool:
        """Delete a booking."""
        stmt = delete(BookingModel).where(BookingModel.id == booking_id)
        result = await self._session.execute(stmt)

        return result.rowcount > 0

    def _model_to_entity(self, model: BookingModel) -> Booking:
        """Convert database model to domain entity."""
        return Booking(
            booking_id=model.id,
            license_plate=model.license_plate,
            appointment_date=model.appointment_date,
            status=model.status,
            user_id=model.user_id,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _slot_model_to_value_object(self, model: TimeSlotModel) -> TimeSlot:
        """Convert database slot model to value object."""
        return TimeSlot(
            date=model.date,
            start_time=model.start_time.time(),
            end_time=model.end_time.time(),
            is_available=model.is_available,
            max_bookings=model.max_bookings,
            current_bookings=model.current_bookings
        )

    def _generate_default_slots(self, target_date: date) -> List[TimeSlot]:
        """Generate default time slots for a date."""
        slots = []

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
            slots.append(slot)

        return slots


class SQLAlchemyVehicleRepository(VehicleRepository):
    """SQLAlchemy implementation of vehicle repository."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, vehicle: Vehicle) -> Vehicle:
        """Save a vehicle to the database."""
        # Check if vehicle exists
        stmt = select(VehicleModel).where(VehicleModel.license_plate == vehicle.license_plate)
        result = await self._session.execute(stmt)
        existing_vehicle = result.scalar_one_or_none()

        if existing_vehicle:
            # Update existing vehicle
            existing_vehicle.make = vehicle.make
            existing_vehicle.model = vehicle.model
            existing_vehicle.year = vehicle.year
            existing_vehicle.vehicle_type = vehicle.__class__.__name__.lower()
            existing_vehicle.updated_at = datetime.utcnow()
        else:
            # Create new vehicle
            vehicle_model = VehicleModel(
                license_plate=vehicle.license_plate,
                make=vehicle.make,
                model=vehicle.model,
                year=vehicle.year,
                vehicle_type=vehicle.__class__.__name__.lower(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self._session.add(vehicle_model)

        await self._session.flush()
        return vehicle

    async def find_by_license_plate(self, license_plate: str) -> Optional[Vehicle]:
        """Find vehicle by license plate."""
        stmt = select(VehicleModel).where(VehicleModel.license_plate == license_plate.upper())
        result = await self._session.execute(stmt)
        vehicle_model = result.scalar_one_or_none()

        if not vehicle_model:
            return None

        return self._model_to_entity(vehicle_model)

    async def find_all(self) -> List[Vehicle]:
        """Find all vehicles."""
        stmt = select(VehicleModel).order_by(VehicleModel.license_plate)
        result = await self._session.execute(stmt)
        vehicle_models = result.scalars().all()

        return [self._model_to_entity(model) for model in vehicle_models]

    async def delete(self, license_plate: str) -> bool:
        """Delete a vehicle."""
        stmt = delete(VehicleModel).where(VehicleModel.license_plate == license_plate.upper())
        result = await self._session.execute(stmt)

        return result.rowcount > 0

    def _model_to_entity(self, model: VehicleModel) -> Vehicle:
        """Convert database model to domain entity."""
        if model.vehicle_type == "car":
            return Car(
                license_plate=model.license_plate,
                make=model.make,
                model=model.model,
                year=model.year
            )
        elif model.vehicle_type == "motorcycle":
            return Motorcycle(
                license_plate=model.license_plate,
                make=model.make,
                model=model.model,
                year=model.year
            )
        else:
            # Default to Car if unknown type
            return Car(
                license_plate=model.license_plate,
                make=model.make,
                model=model.model,
                year=model.year
            )


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of user repository."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_id(self, user_id: UUID) -> Optional[dict]:
        """Find user by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        user_model = result.scalar_one_or_none()

        if not user_model:
            return None

        return {
            "id": user_model.id,
            "email": user_model.email,
            "first_name": user_model.first_name,
            "last_name": user_model.last_name,
            "phone": user_model.phone,
            "is_active": user_model.is_active
        }

    async def exists(self, user_id: UUID) -> bool:
        """Check if user exists."""
        stmt = select(func.count(UserModel.id)).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        count = result.scalar()

        return count > 0


class SQLAlchemyInspectorRepository(InspectorRepository):
    """SQLAlchemy implementation of inspector repository."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, inspector: Inspector) -> Inspector:
        """Save an inspector to the database."""
        # Check if inspector exists
        stmt = select(InspectorModel).where(InspectorModel.id == inspector.id)
        result = await self._session.execute(stmt)
        existing_inspector = result.scalar_one_or_none()

        if existing_inspector:
            # Update existing inspector
            existing_inspector.email = inspector.email
            existing_inspector.first_name = inspector.first_name
            existing_inspector.last_name = inspector.last_name
            existing_inspector.phone = inspector.phone
            existing_inspector.role = inspector.role
            existing_inspector.license_number = inspector.license_number
            existing_inspector.status = inspector.status
            existing_inspector.hire_date = inspector.hire_date
            existing_inspector.updated_at = datetime.utcnow()
        else:
            # Create new inspector
            inspector_model = InspectorModel(
                id=inspector.id,
                email=inspector.email,
                first_name=inspector.first_name,
                last_name=inspector.last_name,
                phone=inspector.phone,
                role=inspector.role,
                license_number=inspector.license_number,
                status=inspector.status,
                hire_date=inspector.hire_date,
                password_hash="",  # Will be set separately
                created_at=inspector.created_at,
                updated_at=datetime.utcnow()
            )
            self._session.add(inspector_model)

        await self._session.flush()
        return inspector

    async def find_by_id(self, inspector_id: UUID) -> Optional[Inspector]:
        """Find inspector by ID."""
        stmt = select(InspectorModel).where(InspectorModel.id == inspector_id)
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            return None

        return self._model_to_entity(inspector_model)

    async def find_by_email(self, email: str) -> Optional[Inspector]:
        """Find inspector by email."""
        stmt = select(InspectorModel).where(InspectorModel.email == email.lower().strip())
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            return None

        return self._model_to_entity(inspector_model)

    async def find_by_license_number(self, license_number: str) -> Optional[Inspector]:
        """Find inspector by license number."""
        stmt = select(InspectorModel).where(InspectorModel.license_number == license_number.upper().strip())
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            return None

        return self._model_to_entity(inspector_model)

    async def find_all_active(self) -> List[Inspector]:
        """Find all active inspectors."""
        stmt = select(InspectorModel).where(
            InspectorModel.status == InspectorStatus.ACTIVE
        ).order_by(InspectorModel.last_name, InspectorModel.first_name)

        result = await self._session.execute(stmt)
        inspector_models = result.scalars().all()

        return [self._model_to_entity(model) for model in inspector_models]

    async def update_password_hash(self, inspector_id: UUID, password_hash: str) -> bool:
        """Update inspector password hash."""
        stmt = select(InspectorModel).where(InspectorModel.id == inspector_id)
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            return False

        inspector_model.password_hash = password_hash
        inspector_model.updated_at = datetime.utcnow()
        await self._session.flush()

        return True

    async def update_login_info(self, inspector_id: UUID, failed_attempts: int = 0, locked_until: Optional[datetime] = None) -> bool:
        """Update inspector login information."""
        stmt = select(InspectorModel).where(InspectorModel.id == inspector_id)
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            return False

        inspector_model.failed_login_attempts = failed_attempts
        inspector_model.locked_until = locked_until
        inspector_model.updated_at = datetime.utcnow()
        await self._session.flush()

        return True

    async def record_login(self, inspector_id: UUID) -> bool:
        """Record successful login."""
        stmt = select(InspectorModel).where(InspectorModel.id == inspector_id)
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            return False

        inspector_model.last_login = datetime.utcnow()
        inspector_model.failed_login_attempts = 0
        inspector_model.locked_until = None
        inspector_model.updated_at = datetime.utcnow()
        await self._session.flush()

        return True

    async def get_password_hash(self, inspector_id: UUID) -> Optional[str]:
        """Get password hash for inspector."""
        stmt = select(InspectorModel.password_hash).where(InspectorModel.id == inspector_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_failed_attempts(self, inspector_id: UUID) -> int:
        """Get number of failed login attempts."""
        stmt = select(InspectorModel.failed_login_attempts).where(InspectorModel.id == inspector_id)
        result = await self._session.execute(stmt)
        failed_attempts = result.scalar_one_or_none()
        return failed_attempts or 0

    async def get_lockout_expiry(self, inspector_id: UUID) -> Optional[datetime]:
        """Get account lockout expiry time."""
        stmt = select(InspectorModel.locked_until).where(InspectorModel.id == inspector_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _model_to_entity(self, model: InspectorModel) -> Inspector:
        """Convert database model to domain entity."""
        return Inspector(
            inspector_id=model.id,
            email=model.email,
            first_name=model.first_name,
            last_name=model.last_name,
            role=model.role,
            license_number=model.license_number,
            status=model.status,
            phone=model.phone,
            hire_date=model.hire_date,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


class InMemoryAuthTokenRepository(AuthTokenRepository):
    """In-memory implementation of auth token repository for development."""

    def __init__(self):
        self._tokens: Dict[str, AuthToken] = {}

    async def save_token(self, token: AuthToken) -> bool:
        """Save authentication token."""
        try:
            self._tokens[token.token] = token
            return True
        except Exception:
            return False

    async def find_token(self, token: str) -> Optional[AuthToken]:
        """Find authentication token."""
        return self._tokens.get(token)

    async def invalidate_token(self, token: str) -> bool:
        """Invalidate authentication token."""
        try:
            if token in self._tokens:
                del self._tokens[token]
                return True
            return False
        except Exception:
            return False

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens."""
        try:
            expired_tokens = [
                token for token, auth_token in self._tokens.items()
                if auth_token.is_expired
            ]

            for token in expired_tokens:
                del self._tokens[token]

            return len(expired_tokens)
        except Exception:
            return 0
