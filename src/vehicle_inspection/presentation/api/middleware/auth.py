"""
Authentication middleware for the vehicle inspection API.

This module provides authentication and authorization functionality
for protecting API endpoints that require inspector authentication.
"""

from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import os
from datetime import datetime, timedelta, timezone

from ....domain.entities.inspector import Inspector
from ....domain.value_objects.auth import LoginCredentials
from ....infrastructure.services import ServiceFactory


# Security scheme for bearer token authentication
security = HTTPBearer()

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails."""
    pass


async def get_current_inspector(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Inspector:
    """
    FastAPI dependency to get the current authenticated inspector.

    This function validates the JWT token from the Authorization header
    and returns the authenticated inspector object.

    Args:
        credentials: HTTP authorization credentials containing the bearer token

    Returns:
        Inspector: The authenticated inspector

    Raises:
        HTTPException: 401 if token is invalid or inspector not found
                      403 if inspector is not active
    """
    if not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        # Extract inspector ID from token
        inspector_id: str = payload.get("sub")
        if inspector_id is None:
            raise AuthenticationError("Invalid token: missing subject")

        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError("Token has expired")

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get inspector from database
    async with ServiceFactory().get_inspector_service() as inspector_service:
        inspector = await inspector_service.get_inspector_by_id(inspector_id)

        if not inspector:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inspector not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not inspector.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inspector account is inactive",
            )

    return inspector


def auth_required(inspector: Inspector = Depends(get_current_inspector)) -> Inspector:
    """
    Decorator dependency for endpoints that require authentication.

    This is a convenience function that can be used as a FastAPI dependency
    to ensure an endpoint requires authentication.

    Args:
        inspector: The authenticated inspector (injected by get_current_inspector)

    Returns:
        Inspector: The authenticated inspector
    """
    return inspector


def create_access_token(inspector_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token for an inspector.

    Args:
        inspector_id: The ID of the inspector
        expires_delta: Optional custom expiration time

    Returns:
        str: The encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)

    to_encode = {
        "sub": inspector_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access_token"
    }

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def authenticate_inspector(credentials: LoginCredentials) -> Optional[str]:
    """
    Authenticate an inspector with username/password and return access token.

    Args:
        credentials: Inspector login credentials

    Returns:
        Optional[str]: Access token if authentication successful, None otherwise
    """
    async with ServiceFactory().get_inspector_service() as inspector_service:
        inspector = await inspector_service.authenticate_inspector(credentials)

        if inspector:
            return create_access_token(inspector.id)

        return None


class TokenResponse:
    """Response model for authentication endpoints."""

    def __init__(self, access_token: str, token_type: str = "bearer"):
        self.access_token = access_token
        self.token_type = token_type


# Optional: Admin-only access decorator
async def get_admin_inspector(
    current_inspector: Inspector = Depends(get_current_inspector)
) -> Inspector:
    """
    Dependency for endpoints that require admin privileges.

    Args:
        current_inspector: The authenticated inspector

    Returns:
        Inspector: The authenticated admin inspector

    Raises:
        HTTPException: 403 if inspector is not an admin
    """
    if not current_inspector.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_inspector


def admin_required(inspector: Inspector = Depends(get_admin_inspector)) -> Inspector:
    """
    Decorator dependency for admin-only endpoints.

    Args:
        inspector: The authenticated admin inspector

    Returns:
        Inspector: The authenticated admin inspector
    """
    return inspector
