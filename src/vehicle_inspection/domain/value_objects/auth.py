"""Authentication-related value objects and services."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID
import hashlib
import secrets
from jose import jwt, JWTError


@dataclass(frozen=True)
class LoginCredentials:
    """Value object for login credentials."""

    email: str
    password: str

    def __post_init__(self) -> None:
        """Validate credentials."""
        if not self.email or not self.email.strip():
            raise ValueError("Email cannot be empty")
        if not self.password or len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if "@" not in self.email:
            raise ValueError("Invalid email format")


@dataclass(frozen=True)
class AuthToken:
    """Value object for JWT authentication token."""

    token: str
    inspector_id: UUID
    expires_at: datetime
    created_at: datetime
    token_type: str = "bearer"

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def time_until_expiry(self) -> timedelta:
        """Get time until token expires."""
        return self.expires_at - datetime.now(timezone.utc)

    @property
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.is_expired


@dataclass(frozen=True)
class LoginResult:
    """Value object for login operation result."""

    success: bool
    inspector_id: Optional[UUID] = None
    token: Optional[AuthToken] = None
    error_message: Optional[str] = None
    locked_until: Optional[datetime] = None
    failed_attempts: int = 0


class PasswordHasher:
    """Service for password hashing and verification."""

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash a password with salt."""
        if salt is None:
            salt = secrets.token_hex(32)

        # Using PBKDF2 with SHA-256
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,  # iterations
        )

        return hashed.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Verify a password against its hash."""
        new_hash, _ = PasswordHasher.hash_password(password, salt)
        return secrets.compare_digest(new_hash, hashed_password)

    @staticmethod
    def create_password_hash(password: str) -> str:
        """Create a complete password hash with embedded salt."""
        hashed, salt = PasswordHasher.hash_password(password)
        return f"{salt}:{hashed}"

    @staticmethod
    def verify_password_hash(password: str, password_hash: str) -> bool:
        """Verify password against complete hash."""
        try:
            salt, hashed = password_hash.split(":", 1)
            return PasswordHasher.verify_password(password, hashed, salt)
        except ValueError:
            return False


class TokenGenerator:
    """Service for generating JWT authentication tokens following FastAPI best practices."""

    @staticmethod
    def generate_jwt_token(
        inspector_id: UUID,
        secret_key: str,
        algorithm: str = "HS256",
        expires_in_hours: int = 8,
    ) -> AuthToken:
        """
        Generate a JWT token for an inspector.

        Follows the FastAPI OAuth2 with JWT pattern from:
        https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/

        Args:
            inspector_id: UUID of the inspector
            secret_key: Secret key for signing the token
            algorithm: JWT algorithm (default: HS256)
            expires_in_hours: Token expiration time in hours

        Returns:
            AuthToken: The generated JWT token with metadata
        """
        # Calculate expiration time
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=expires_in_hours)

        # Create JWT payload
        payload: Dict[str, Any] = {
            "sub": str(inspector_id),  # Subject (inspector ID)
            "iat": created_at,  # Issued at
            "exp": expires_at,  # Expiration time
        }

        # Encode JWT token
        try:
            encoded_jwt = jwt.encode(payload, secret_key, algorithm=algorithm)
        except Exception as e:
            raise ValueError(f"Failed to encode JWT token: {str(e)}")

        return AuthToken(
            token=encoded_jwt,
            inspector_id=inspector_id,
            expires_at=expires_at,
            created_at=created_at,
            token_type="bearer",
        )

    @staticmethod
    def verify_jwt_token(
        token: str,
        secret_key: str,
        algorithm: str = "HS256",
    ) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token to verify
            secret_key: Secret key for verifying the token
            algorithm: JWT algorithm used

        Returns:
            Dict containing the decoded payload

        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid or expired token: {str(e)}")

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token (for backward compatibility)."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_auth_token(
        inspector_id: UUID,
        expires_in_hours: int = 8,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
    ) -> AuthToken:
        """
        Create an authentication token.

        Wrapper method for generating JWT tokens. If secret_key is provided,
        creates a JWT token. Otherwise, creates a simple token.

        Args:
            inspector_id: UUID of the inspector
            expires_in_hours: Token expiration time in hours
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm

        Returns:
            AuthToken: The generated token
        """
        if secret_key:
            return TokenGenerator.generate_jwt_token(
                inspector_id=inspector_id,
                secret_key=secret_key,
                algorithm=algorithm,
                expires_in_hours=expires_in_hours,
            )

        # Fallback to simple token generation
        token = TokenGenerator.generate_token()
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=expires_in_hours)

        return AuthToken(
            token=token,
            inspector_id=inspector_id,
            expires_at=expires_at,
            created_at=created_at,
        )
