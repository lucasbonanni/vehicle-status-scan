"""SQLAlchemy repository implementations."""

import json
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, and_, func, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.vehicle_inspection.infrastructure.logging import (
    get_logger,
    log_database_operation
)

from src.vehicle_inspection.application.ports.repositories import BookingRepository, VehicleRepository, UserRepository, InspectorRepository, AuthTokenRepository, InspectionRepository
from src.vehicle_inspection.domain.entities.booking import Booking, BookingStatus
from src.vehicle_inspection.domain.entities.vehicle import Vehicle, Car, Motorcycle
from src.vehicle_inspection.domain.entities.inspector import Inspector, InspectorRole, InspectorStatus
from src.vehicle_inspection.domain.entities.inspection import Inspection, InspectionStatus
from src.vehicle_inspection.domain.value_objects.time_slot import TimeSlot
from src.vehicle_inspection.domain.value_objects.auth import AuthToken
from src.vehicle_inspection.domain.value_objects.checkpoint_score import CheckpointScore
from src.vehicle_inspection.domain.value_objects.checkpoint_types import CheckpointType
from src.vehicle_inspection.infrastructure.database.models import BookingModel, TimeSlotModel, VehicleModel, UserModel, InspectorModel, InspectionModel


class SQLAlchemyBookingRepository(BookingRepository):
    """SQLAlchemy implementation of booking repository."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._logger = get_logger(__name__)

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
        log_database_operation(
            self._logger,
            "SELECT",
            "TimeSlotModel",
            extra={"target_date": str(target_date)}
        )

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
            self._logger.debug(
                "Found existing time slots in database",
                extra={"slot_count": len(slot_models), "date": str(target_date)}
            )
            return [self._slot_model_to_value_object(model) for model in slot_models]
        else:
            # Generate default slots if none exist
            self._logger.info(
                "No existing slots found, generating default slots",
                extra={"date": str(target_date)}
            )
            return self._generate_default_slots(target_date)

    async def is_slot_available(self, appointment_date: datetime) -> bool:
        """Check if a specific datetime slot is available."""
        log_database_operation(
            self._logger,
            "SELECT",
            "BookingModel",
            extra={"appointment_date": str(appointment_date), "operation": "availability_check"}
        )

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
        is_available = booking_count < 1
        self._logger.debug(
            "Slot availability check completed",
            extra={
                "appointment_date": str(appointment_date),
                "booking_count": booking_count,
                "is_available": is_available
            }
        )
        return is_available

    async def delete(self, booking_id: UUID) -> bool:
        """Delete a booking."""
        log_database_operation(
            self._logger,
            "DELETE",
            "BookingModel",
            extra={"booking_id": str(booking_id)}
        )

        stmt = delete(BookingModel).where(BookingModel.id == booking_id)
        result = await self._session.execute(stmt)

        success = result.rowcount > 0
        if success:
            self._logger.info(
                "Booking deleted successfully",
                extra={"booking_id": str(booking_id), "rows_affected": result.rowcount}
            )
        else:
            self._logger.warning(
                "Booking deletion failed - not found",
                extra={"booking_id": str(booking_id)}
            )

        return success

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
        self._logger = get_logger(__name__)

    async def save(self, inspector: Inspector) -> Inspector:
        """Save an inspector to the database."""
        # Check if inspector exists
        stmt = select(InspectorModel).where(InspectorModel.id == inspector.id)
        result = await self._session.execute(stmt)
        existing_inspector = result.scalar_one_or_none()

        if existing_inspector:
            # Update existing inspector
            log_database_operation(
                self._logger,
                "UPDATE",
                "InspectorModel",
                extra={"inspector_id": str(inspector.id), "email": inspector.email}
            )

            existing_inspector.email = inspector.email
            existing_inspector.first_name = inspector.first_name
            existing_inspector.last_name = inspector.last_name
            existing_inspector.phone = inspector.phone
            existing_inspector.role = inspector.role
            existing_inspector.license_number = inspector.license_number
            existing_inspector.status = inspector.status
            existing_inspector.hire_date = inspector.hire_date
            existing_inspector.updated_at = datetime.utcnow()

            self._logger.info(
                "Inspector updated successfully",
                extra={"inspector_id": str(inspector.id), "email": inspector.email}
            )
        else:
            # Create new inspector
            log_database_operation(
                self._logger,
                "INSERT",
                "InspectorModel",
                extra={"inspector_id": str(inspector.id), "email": inspector.email}
            )

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

            self._logger.info(
                "New inspector created successfully",
                extra={"inspector_id": str(inspector.id), "email": inspector.email}
            )

        await self._session.flush()
        return inspector

    async def find_by_id(self, inspector_id: UUID) -> Optional[Inspector]:
        """Find inspector by ID."""
        log_database_operation(
            self._logger,
            "SELECT",
            "InspectorModel",
            extra={"inspector_id": str(inspector_id), "lookup_field": "id"}
        )

        stmt = select(InspectorModel).where(InspectorModel.id == inspector_id)
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            self._logger.debug(
                "Inspector not found by ID",
                extra={"inspector_id": str(inspector_id)}
            )
            return None

        self._logger.debug(
            "Inspector found by ID",
            extra={"inspector_id": str(inspector_id), "email": inspector_model.email}
        )
        return self._model_to_entity(inspector_model)

    async def find_by_email(self, email: str) -> Optional[Inspector]:
        """Find inspector by email."""
        sanitized_email = email.lower().strip()
        log_database_operation(
            self._logger,
            "SELECT",
            "InspectorModel",
            extra={"email": sanitized_email, "lookup_field": "email"}
        )

        stmt = select(InspectorModel).where(InspectorModel.email == sanitized_email)
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            self._logger.debug(
                "Inspector not found by email",
                extra={"email": sanitized_email}
            )
            return None

        self._logger.debug(
            "Inspector found by email",
            extra={"email": sanitized_email, "inspector_id": str(inspector_model.id)}
        )
        return self._model_to_entity(inspector_model)

    async def find_by_license_number(self, license_number: str) -> Optional[Inspector]:
        """Find inspector by license number."""
        sanitized_license = license_number.upper().strip()
        log_database_operation(
            self._logger,
            "SELECT",
            "InspectorModel",
            extra={"license_number": sanitized_license, "lookup_field": "license_number"}
        )

        stmt = select(InspectorModel).where(InspectorModel.license_number == sanitized_license)
        result = await self._session.execute(stmt)
        inspector_model = result.scalar_one_or_none()

        if not inspector_model:
            self._logger.debug(
                "Inspector not found by license number",
                extra={"license_number": sanitized_license}
            )
            return None

        self._logger.debug(
            "Inspector found by license number",
            extra={"license_number": sanitized_license, "inspector_id": str(inspector_model.id)}
        )
        return self._model_to_entity(inspector_model)

    async def find_all_active(self) -> List[Inspector]:
        """Find all active inspectors."""
        log_database_operation(
            self._logger,
            "SELECT",
            "InspectorModel",
            extra={"filter": "status=ACTIVE", "operation": "find_all_active"}
        )

        stmt = select(InspectorModel).where(
            InspectorModel.status == InspectorStatus.ACTIVE
        ).order_by(InspectorModel.last_name, InspectorModel.first_name)

        result = await self._session.execute(stmt)
        inspector_models = result.scalars().all()

        self._logger.info(
            "Found active inspectors",
            extra={"count": len(inspector_models)}
        )
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


class SQLAlchemyInspectionRepository(InspectionRepository):
    """SQLAlchemy implementation of inspection repository."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._logger = get_logger(__name__)

    async def save(self, inspection: Inspection) -> Inspection:
        """Save an inspection to the database."""
        # Check if inspection exists
        stmt = select(InspectionModel).where(InspectionModel.id == inspection.id)
        result = await self._session.execute(stmt)
        existing_inspection = result.scalar_one_or_none()

        if existing_inspection:
            # Update existing inspection
            log_database_operation(self._logger, "UPDATE", "inspections",
                                 inspection_id=str(inspection.id),
                                 license_plate=inspection.license_plate)
            self._update_model_from_entity(existing_inspection, inspection)
            existing_inspection.updated_at = datetime.utcnow()
        else:
            # Create new inspection
            log_database_operation(self._logger, "INSERT", "inspections",
                                 inspection_id=str(inspection.id),
                                 license_plate=inspection.license_plate)
            inspection_model = self._entity_to_model(inspection)
            self._session.add(inspection_model)

        await self._session.flush()
        return inspection

    async def find_by_id(self, inspection_id: UUID) -> Optional[Inspection]:
        """Find inspection by ID."""
        log_database_operation(self._logger, "SELECT", "inspections",
                             inspection_id=str(inspection_id))
        stmt = select(InspectionModel).where(InspectionModel.id == inspection_id)
        result = await self._session.execute(stmt)
        inspection_model = result.scalar_one_or_none()

        if not inspection_model:
            return None

        return self._model_to_entity(inspection_model)

    async def find_by_license_plate(self, license_plate: str) -> List[Inspection]:
        """Find all inspections for a license plate (ordered by created_at DESC)."""
        normalized_plate = license_plate.upper().replace(" ", "").replace("-", "")

        stmt = select(InspectionModel).where(
            InspectionModel.license_plate == normalized_plate
        ).order_by(desc(InspectionModel.created_at))

        result = await self._session.execute(stmt)
        inspection_models = result.scalars().all()

        return [self._model_to_entity(model) for model in inspection_models]

    async def find_latest_by_license_plate(self, license_plate: str) -> Optional[Inspection]:
        """Find the most recent inspection for a license plate."""
        normalized_plate = license_plate.upper().replace(" ", "").replace("-", "")

        stmt = select(InspectionModel).where(
            InspectionModel.license_plate == normalized_plate
        ).order_by(desc(InspectionModel.created_at)).limit(1)

        result = await self._session.execute(stmt)
        inspection_model = result.scalar_one_or_none()

        if not inspection_model:
            return None

        return self._model_to_entity(inspection_model)

    async def find_by_inspector(self, inspector_id: UUID) -> List[Inspection]:
        """Find all inspections performed by a specific inspector."""
        stmt = select(InspectionModel).where(
            InspectionModel.inspector_id == inspector_id
        ).order_by(desc(InspectionModel.created_at))

        result = await self._session.execute(stmt)
        inspection_models = result.scalars().all()

        return [self._model_to_entity(model) for model in inspection_models]

    async def find_by_status(self, status: str) -> List[Inspection]:
        """Find all inspections with a specific status (draft/completed)."""
        stmt = select(InspectionModel).where(
            InspectionModel.status == InspectionStatus(status)
        ).order_by(desc(InspectionModel.created_at))

        result = await self._session.execute(stmt)
        inspection_models = result.scalars().all()

        return [self._model_to_entity(model) for model in inspection_models]

    async def find_completed_inspections(self, limit: Optional[int] = None) -> List[Inspection]:
        """Find completed inspections, optionally limited by count."""
        stmt = select(InspectionModel).where(
            InspectionModel.status == InspectionStatus.COMPLETED
        ).order_by(desc(InspectionModel.completed_at))

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        inspection_models = result.scalars().all()

        return [self._model_to_entity(model) for model in inspection_models]

    async def find_draft_inspections_by_inspector(self, inspector_id: UUID) -> List[Inspection]:
        """Find all draft inspections for a specific inspector."""
        stmt = select(InspectionModel).where(
            and_(
                InspectionModel.inspector_id == inspector_id,
                InspectionModel.status == InspectionStatus.DRAFT
            )
        ).order_by(desc(InspectionModel.updated_at))

        result = await self._session.execute(stmt)
        inspection_models = result.scalars().all()

        return [self._model_to_entity(model) for model in inspection_models]

    async def update(self, inspection: Inspection) -> Inspection:
        """Update an existing inspection."""
        stmt = select(InspectionModel).where(InspectionModel.id == inspection.id)
        result = await self._session.execute(stmt)
        inspection_model = result.scalar_one_or_none()

        if not inspection_model:
            raise ValueError(f"Inspection with ID {inspection.id} not found")

        self._update_model_from_entity(inspection_model, inspection)
        inspection_model.updated_at = datetime.utcnow()

        await self._session.flush()
        return inspection

    async def delete(self, inspection_id: UUID) -> bool:
        """Delete an inspection by ID."""
        stmt = delete(InspectionModel).where(InspectionModel.id == inspection_id)
        result = await self._session.execute(stmt)

        return result.rowcount > 0

    async def exists(self, inspection_id: UUID) -> bool:
        """Check if an inspection exists."""
        stmt = select(func.count(InspectionModel.id)).where(
            InspectionModel.id == inspection_id
        )
        result = await self._session.execute(stmt)
        count = result.scalar()

        return count > 0

    async def count_by_inspector(self, inspector_id: UUID) -> int:
        """Count total inspections by inspector."""
        stmt = select(func.count(InspectionModel.id)).where(
            InspectionModel.inspector_id == inspector_id
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def count_by_license_plate(self, license_plate: str) -> int:
        """Count total inspections for a license plate."""
        normalized_plate = license_plate.upper().replace(" ", "").replace("-", "")

        stmt = select(func.count(InspectionModel.id)).where(
            InspectionModel.license_plate == normalized_plate
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    def _model_to_entity(self, model: InspectionModel) -> Inspection:
        """Convert database model to domain entity."""
        # Deserialize checkpoint scores from JSON
        checkpoint_scores = []
        if model.checkpoint_scores:
            scores_data = json.loads(model.checkpoint_scores) if isinstance(model.checkpoint_scores, str) else model.checkpoint_scores
            for score_data in scores_data:
                checkpoint_scores.append(CheckpointScore(
                    checkpoint_type=CheckpointType(score_data['checkpoint_type']),
                    score=score_data['score'],
                    notes=score_data.get('notes', '')
                ))

        return Inspection(
            license_plate=model.license_plate,
            vehicle_type=model.vehicle_type,
            inspector_id=model.inspector_id,
            inspection_id=model.id,
            checkpoint_scores=checkpoint_scores,
            observations=model.observations or "",
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at
        )

    def _entity_to_model(self, inspection: Inspection) -> InspectionModel:
        """Convert domain entity to database model."""
        # Serialize checkpoint scores to JSON
        checkpoint_scores_json = None
        if inspection.checkpoint_scores:
            scores_data = []
            for score in inspection.checkpoint_scores:
                scores_data.append({
                    'checkpoint_type': score.checkpoint_type.value,
                    'score': score.score,
                    'notes': score.notes
                })
            checkpoint_scores_json = json.dumps(scores_data)

        return InspectionModel(
            id=inspection.id,
            license_plate=inspection.license_plate.upper().replace(" ", "").replace("-", ""),
            vehicle_type=inspection.vehicle_type,
            inspector_id=inspection.inspector_id,
            checkpoint_scores=checkpoint_scores_json,
            total_score=inspection.get_total_score() if inspection.checkpoint_scores else None,
            is_safe=inspection.is_safe() if inspection.checkpoint_scores else None,
            requires_reinspection=inspection.requires_reinspection() if inspection.checkpoint_scores else None,
            observations=inspection.observations,
            status=inspection.status,
            created_at=inspection.created_at,
            updated_at=inspection.updated_at,
            completed_at=inspection.completed_at
        )

    def _update_model_from_entity(self, model: InspectionModel, inspection: Inspection) -> None:
        """Update database model fields from domain entity."""
        # Serialize checkpoint scores to JSON
        checkpoint_scores_json = None
        if inspection.checkpoint_scores:
            scores_data = []
            for score in inspection.checkpoint_scores:
                scores_data.append({
                    'checkpoint_type': score.checkpoint_type.value,
                    'score': score.score,
                    'notes': score.notes
                })
            checkpoint_scores_json = json.dumps(scores_data)

        model.license_plate = inspection.license_plate.upper().replace(" ", "").replace("-", "")
        model.vehicle_type = inspection.vehicle_type
        model.inspector_id = inspection.inspector_id
        model.checkpoint_scores = checkpoint_scores_json
        model.total_score = inspection.get_total_score() if inspection.checkpoint_scores else None
        model.is_safe = inspection.is_safe() if inspection.checkpoint_scores else None
        model.requires_reinspection = inspection.requires_reinspection() if inspection.checkpoint_scores else None
        model.observations = inspection.observations
        model.status = inspection.status
        model.completed_at = inspection.completed_at


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
