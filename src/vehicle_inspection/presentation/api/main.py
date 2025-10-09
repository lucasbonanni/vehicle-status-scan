"""FastAPI main application module."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from ...infrastructure.services import initialize_services, shutdown_services
from .routes import health, vehicles, bookings, inspections, auth
from .config import get_settings
from .middleware.auth import AuthenticationError, AuthorizationError


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Vehicle Inspection System API")
    await initialize_services()

    yield

    # Shutdown
    logger.info("Shutting down Vehicle Inspection System API")
    await shutdown_services()


def add_exception_handlers(app: FastAPI) -> None:
    """Add custom exception handlers to the FastAPI application."""

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        """Handle authentication errors."""
        logger.warning(f"Authentication error on {request.url}: {str(exc)}")
        return JSONResponse(
            status_code=401,
            content={
                "detail": str(exc),
                "type": "authentication_error"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError):
        """Handle authorization errors."""
        logger.warning(f"Authorization error on {request.url}: {str(exc)}")
        return JSONResponse(
            status_code=403,
            content={
                "detail": str(exc),
                "type": "authorization_error"
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle validation errors from business logic."""
        logger.warning(f"Validation error on {request.url}: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={
                "detail": str(exc),
                "type": "validation_error"
            }
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        """Handle runtime errors from business logic."""
        logger.error(f"Runtime error on {request.url}: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error occurred",
                "type": "runtime_error"
            }
        )


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

    # Add custom exception handlers
    add_exception_handlers(app)

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
