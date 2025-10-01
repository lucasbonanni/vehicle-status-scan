"""Dependency injection and service factory."""

import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from src.vehicle_inspection.infrastructure.database.connection import DatabaseManager
from src.vehicle_inspection.infrastructure.repositories.sql_repositories import (
    SQLAlchemyBookingRepository,
    SQLAlchemyVehicleRepository,
    SQLAlchemyUserRepository
)
from src.vehicle_inspection.application.services.booking_service import BookingService


class ServiceFactory:
    """Factory for creating application services with proper dependencies."""

    def __init__(self, database_url: str):
        self.database_manager = DatabaseManager(database_url)
        self._connected = False

    async def initialize(self):
        """Initialize the service factory."""
        if not self._connected:
            await self.database_manager.connect()
            self._connected = True

    async def shutdown(self):
        """Shutdown the service factory."""
        if self._connected:
            await self.database_manager.disconnect()
            self._connected = False

    @asynccontextmanager
    async def get_booking_service(self) -> AsyncGenerator[BookingService, None]:
        """Get booking service with database repositories."""
        async with self.database_manager.get_session() as session:
            booking_repo = SQLAlchemyBookingRepository(session)
            vehicle_repo = SQLAlchemyVehicleRepository(session)
            user_repo = SQLAlchemyUserRepository(session)

            service = BookingService(
                booking_repository=booking_repo,
                vehicle_repository=vehicle_repo,
                user_repository=user_repo
            )

            yield service


# Global service factory instance
_service_factory: ServiceFactory | None = None


def get_service_factory() -> ServiceFactory:
    """Get the global service factory instance."""
    global _service_factory

    if _service_factory is None:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:password@localhost:5432/vehicle_inspection"
        )
        _service_factory = ServiceFactory(database_url)

    return _service_factory


async def initialize_services():
    """Initialize application services."""
    factory = get_service_factory()
    await factory.initialize()


async def shutdown_services():
    """Shutdown application services."""
    factory = get_service_factory()
    await factory.shutdown()
