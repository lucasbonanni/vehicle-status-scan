"""FastAPI main application module."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from ...infrastructure.services import initialize_services, shutdown_services
from .routes import health, vehicles, bookings, inspections, auth
from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    await initialize_services()

    yield

    # Shutdown
    await shutdown_services()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Vehicle Inspection System",
        description="API for managing vehicle inspections with 8-point evaluation system",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )

    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(
        auth.router,
        prefix=f"{settings.api_prefix}/auth",
        tags=["authentication"]
    )
    app.include_router(
        vehicles.router,
        prefix=f"{settings.api_prefix}/vehicles",
        tags=["vehicles"]
    )
    app.include_router(
        bookings.router,
        prefix=f"{settings.api_prefix}/bookings",
        tags=["bookings"]
    )
    app.include_router(
        inspections.router,
        prefix=f"{settings.api_prefix}/inspections",
        tags=["inspections"]
    )

    return app


# Create app instance
app = create_app()
