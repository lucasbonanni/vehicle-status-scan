"""Authentication endpoints for inspector login."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from src.vehicle_inspection.domain.value_objects.auth import LoginCredentials, LoginResult
from src.vehicle_inspection.infrastructure.services import get_service_factory

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    success: bool
    token: Optional[str] = None
    inspector_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    locked_until: Optional[datetime] = None
    failed_attempts: int = 0


class InspectorProfile(BaseModel):
    """Inspector profile response model."""
    id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    role: str
    license_number: str
    status: str
    hire_date: datetime
    can_perform_inspections: bool
    is_supervisor: bool


class ChangePasswordRequest(BaseModel):
    """Change password request model."""
    old_password: str
    new_password: str


class ApiResponse(BaseModel):
    """Generic API response model."""
    success: bool
    message: str


async def get_auth_service():
    """Dependency to get authentication service."""
    service_factory = get_service_factory()
    async with service_factory.get_auth_service() as auth_service:
        yield auth_service


async def get_current_inspector(
    authorization: str = Header(None),
    auth_service = Depends(get_auth_service)
):
    """Dependency to get current authenticated inspector."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.split(" ")[1]
    inspector = await auth_service.validate_token(token)

    if not inspector:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return inspector


@router.post("/login")
async def login(
    request: LoginRequest,
    auth_service = Depends(get_auth_service)
) -> LoginResponse:
    """Authenticate inspector and return access token."""
    try:
        # Create login credentials
        credentials = LoginCredentials(
            email=request.email,
            password=request.password
        )

        # Attempt login
        result = await auth_service.login(credentials)

        if result.success and result.token:
            return LoginResponse(
                success=True,
                token=result.token.token,
                inspector_id=str(result.inspector_id),
                expires_at=result.token.expires_at
            )
        else:
            return LoginResponse(
                success=False,
                error_message=result.error_message,
                locked_until=result.locked_until,
                failed_attempts=result.failed_attempts
            )

    except ValueError as e:
        return LoginResponse(
            success=False,
            error_message=str(e)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service error")


@router.post("/logout")
async def logout(
    authorization: str = Header(None),
    auth_service = Depends(get_auth_service)
) -> ApiResponse:
    """Logout inspector by invalidating token."""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authentication required")

        token = authorization.split(" ")[1]
        success = await auth_service.logout(token)

        return ApiResponse(
            success=success,
            message="Logged out successfully" if success else "Logout failed"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Logout service error")


@router.get("/profile")
async def get_profile(
    current_inspector = Depends(get_current_inspector)
) -> InspectorProfile:
    """Get current inspector profile."""
    return InspectorProfile(
        id=str(current_inspector.id),
        email=current_inspector.email,
        first_name=current_inspector.first_name,
        last_name=current_inspector.last_name,
        full_name=current_inspector.full_name,
        role=current_inspector.role.value,
        license_number=current_inspector.license_number,
        status=current_inspector.status.value,
        hire_date=current_inspector.hire_date,
        can_perform_inspections=current_inspector.can_perform_inspections(),
        is_supervisor=current_inspector.is_supervisor()
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_inspector = Depends(get_current_inspector),
    auth_service = Depends(get_auth_service)
) -> ApiResponse:
    """Change inspector password."""
    try:
        success = await auth_service.change_password(
            current_inspector.id,
            request.old_password,
            request.new_password
        )

        if success:
            return ApiResponse(
                success=True,
                message="Password changed successfully"
            )
        else:
            return ApiResponse(
                success=False,
                message="Failed to change password. Please check your old password."
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Password change service error")


@router.post("/validate-token")
async def validate_token(
    current_inspector = Depends(get_current_inspector)
) -> ApiResponse:
    """Validate current authentication token."""
    return ApiResponse(
        success=True,
        message=f"Token is valid for inspector: {current_inspector.full_name}"
    )
